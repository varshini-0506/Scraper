import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import asyncio

SEARCH_URL = "https://www.flipkart.com/search?q={}"

# Multiple User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_headers():
    """Get random headers with User-Agent rotation"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.google.com/",
        "Origin": "https://www.flipkart.com"
    }

def create_session():
    """Create a session with retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def scrape_flipkart(query: str, max_results: int = 20):
    """
    Robust requests-based scraper for Flipkart
    """
    try:
        session = create_session()
        url = SEARCH_URL.format(query.replace(' ', '+'))
        print(f"🔍 Scraping Flipkart for: {query}")

        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))

        try:
            response = session.get(url, headers=get_headers(), timeout=30)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            print("❌ Request timed out, trying with shorter timeout...")
            response = session.get(url, headers=get_headers(), timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            # Try with different headers
            headers = get_headers()
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            response = session.get(url, headers=headers, timeout=20)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html5lib")

        # Try multiple selectors for different page layouts
        product_selectors = [
            "div[data-id]",  # Generic data-id selector
            "div._13oc-S",   # Traditional grid layout
            "div._1AtVbE",   # Alternative layout
            "div._2kHMtA",   # Another layout
            "div._3pLy-c",   # Another layout
            "div[class*='product']",  # Generic product selector
            "div[class*='item']"      # Generic item selector
        ]

        items = []
        for selector in product_selectors:
            items = soup.select(selector)
            if items:
                print(f"✅ Found {len(items)} products with selector: {selector}")
                break

        if not items:
            print("❌ No products found with any selector")
            return []

        results = []
        for i, item in enumerate(items[:max_results]):
            try:
                # Debug: Print item HTML for first few items
                if i < 3:
                    print(f"🔍 Item {i} HTML snippet: {str(item)[:300]}...")

                # Extract link - try multiple selectors
                link = None
                link_selectors = [
                    "a._1fQZEK", "a.s1Q9rs", "a[href*='/p/']", "a[href*='flipkart.com']",
                    "a[href*='product']", "a", "[data-testid*='product'] a"
                ]
                for selector in link_selectors:
                    a = item.select_one(selector)
                    if a and a.has_attr("href"):
                        href = a["href"].split("?")[0]
                        link = f"https://www.flipkart.com{href}" if href.startswith("/") else href
                        break

                # Extract title - try multiple selectors and methods
                title = None
                title_selectors = [
                    "div._4rR01T", "a.s1Q9rs", "div._2WkVRV", "span.B_NuCI",
                    "div._3pLy-c", "div._2kHMtA", "div._1AtVbE",
                    "h3", "h2", "h1", "div[class*='title']", "span[class*='title']",
                    "div[class*='name']", "span[class*='name']", "div[class*='product']",
                    "a.VJA3rP", "a[class*='VJA3rP']", "div.slAVV4 a"
                ]
                for selector in title_selectors:
                    t = item.select_one(selector)
                    if t:
                        title = t.get_text(strip=True)
                        if title and len(title) > 3:
                            break

                # If no title found, try to extract from link href (product name in URL)
                if not title:
                    a = item.select_one("a")
                    if a and a.has_attr("href"):
                        href = a["href"]
                        if i < 3:
                            print(f"🔍 Item {i} href: {href}")
                        # Extract product name from URL path - the part before /p/
                        if "/p/" in href:
                            # Extract everything before /p/ and clean it up
                            match = re.search(r'/([^/]+)/p/', href)
                            if match:
                                product_name = match.group(1)
                                # Replace hyphens with spaces and clean up
                                title = product_name.replace("-", " ").replace("_", " ")
                                # Remove common suffixes and clean up
                                title = re.sub(r'\b(pid|lid|marketplace|store|q|amp).*', '', title)
                                title = title.strip()
                                if i < 3:
                                    print(f"🔍 Item {i} extracted title from URL: '{title}'")

                # If still no title, try to extract from link text
                if not title:
                    a = item.select_one("a")
                    if a:
                        title = a.get_text(strip=True)

                # If still no title, try to find any meaningful text in the item
                if not title:
                    all_text = item.get_text(strip=True)
                    # Split by common separators and find the longest meaningful text
                    text_parts = re.split(r'[₹\n\t]', all_text)
                    for part in text_parts:
                        if len(part.strip()) > 10 and not re.match(r'^\d+$', part.strip()):
                            title = part.strip()
                            break

                # Extract price using regex as primary method
                price = None
                price_text = item.get_text()
                price_match = re.search(r'₹[\d,]+', price_text)
                if price_match:
                    price = price_match.group()
                else:
                    # Try CSS selectors
                    price_selectors = [
                        "div._30jeq3", "div._1vC4OE", "span._2-ut7f", "div[class*='price']",
                        "span[class*='price']", "div[class*='cost']", "span[class*='cost']"
                    ]
                    for selector in price_selectors:
                        p = item.select_one(selector)
                        if p:
                            price_text = p.get_text(strip=True)
                            if '₹' in price_text or re.search(r'\d+', price_text):
                                price = price_text
                                break

                # Extract rating using regex as primary method
                rating = None
                rating_match = re.search(r'(\d+\.\d+)', price_text)
                if rating_match:
                    rating_val = float(rating_match.group(1))
                    if 1.0 <= rating_val <= 5.0:  # Filter for valid ratings
                        rating = str(rating_val)

                if not rating:
                    # Try CSS selectors
                    rating_selectors = [
                        "div._3LWZlK", "span._2_KrJI", "div._3i9_wc", "div[class*='rating']",
                        "span[class*='rating']", "div[class*='star']", "span[class*='star']"
                    ]
                    for selector in rating_selectors:
                        r = item.select_one(selector)
                        if r:
                            rating_text = r.get_text(strip=True)
                            rating_match = re.search(r'(\d+\.\d+)', rating_text)
                            if rating_match:
                                rating_val = float(rating_match.group(1))
                                if 1.0 <= rating_val <= 5.0:
                                    rating = str(rating_val)
                                    break

                # Extract image - try multiple selectors
                image = None
                img_selectors = [
                    "img._396cs4", "img._2r_T1I", "img._3exPp9", "img[class*='product']",
                    "img[class*='item']", "img", "[data-testid*='image'] img"
                ]
                for selector in img_selectors:
                    img = item.select_one(selector)
                    if img and img.has_attr("src"):
                        src = img.get("src")
                        if src:
                            image = src if src.startswith("http") else f"https:{src}" if src.startswith("//") else None
                            break

                # Debug: Print extracted data for first few items
                if i < 3:
                    print(f"📊 Item {i} extracted: title='{title}', price='{price}', rating='{rating}'")
                    print(f"🔗 Link: {link}")
                    print(f"🖼️ Image: {image}")
                    print(f"🔍 Title length: {len(title.strip()) if title else 0}")
                    print(f"🔍 Title check: {bool(title and len(title.strip()) > 3)}")

                # Only add if we have at least a title
                if title and len(title.strip()) > 3:
                    print(f"✅ Adding item {i}: '{title}'")
                    results.append({
                        "title": title,
                        "link": link,
                        "image": image,
                        "price": price,
                        "rating": rating
                    })
                else:
                    if i < 3:
                        print(f"⚠️ Skipping item {i} - no valid title found (title='{title}', length={len(title.strip()) if title else 0})")

            except Exception as e:
                print(f"⚠️ Error processing item {i}: {e}")
                continue

        print(f"✅ Successfully scraped {len(results)} products from Flipkart")
        return results

    except Exception as e:
        print(f"❌ Error scraping Flipkart: {e}")
        # Return a fallback response with mock data
        print("🔄 Returning fallback data due to scraping error")
        return [{
            "title": f"{query} - Product not available",
            "link": "https://www.flipkart.com",
            "image": None,
            "price": "Price not available",
            "rating": None
        }]

# Create a scraper object that main.py expects
class FlipkartScraper:
    def __init__(self):
        pass

    async def scrape(self, query: str, max_results: int = 20):
        # Run the synchronous scraper in a thread to make it async
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, scrape_flipkart, query, max_results)

scraper = FlipkartScraper()
