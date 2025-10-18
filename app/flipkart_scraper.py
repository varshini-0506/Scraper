import requests
from bs4 import BeautifulSoup
import random
import re

def scrape_flipkart(query: str, max_results: int = 20):
    """
    Robust requests-based scraper for Flipkart
    """
    try:
        # Multiple User-Agents for rotation
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        print(f"🔍 Scraping Flipkart for: {query}")
        
        response = requests.get(url, headers=headers, timeout=15)
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
                # Extract link
                link = None
                link_selectors = ["a._1fQZEK", "a.s1Q9rs", "a[href*='/p/']", "a[href*='flipkart.com']"]
                for selector in link_selectors:
                    a = item.select_one(selector)
                    if a and a.has_attr("href"):
                        href = a["href"].split("?")[0]
                        link = f"https://www.flipkart.com{href}" if href.startswith("/") else href
                        break
                
                # Extract title
                title = None
                title_selectors = [
                    "div._4rR01T", "a.s1Q9rs", "div._2WkVRV", "span.B_NuCI",
                    "div._3pLy-c", "div._2kHMtA", "div._1AtVbE",
                    "h3", "h2", "h1", "div[class*='title']", "span[class*='title']"
                ]
                for selector in title_selectors:
                    t = item.select_one(selector)
                    if t:
                        title = t.get_text(strip=True)
                        if title and len(title) > 3:
                            break
                
                # If no title found, try to extract from link text
                if not title:
                    a = item.select_one("a")
                    if a:
                        title = a.get_text(strip=True)
                
                # Extract price using regex as primary method
                price = None
                price_text = item.get_text()
                price_match = re.search(r'₹[\d,]+', price_text)
                if price_match:
                    price = price_match.group()
                else:
                    # Try CSS selectors
                    price_selectors = ["div._30jeq3", "div._1vC4OE", "span._2-ut7f", "div[class*='price']"]
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
                    rating_selectors = ["div._3LWZlK", "span._2_KrJI", "div._3i9_wc", "div[class*='rating']"]
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
                
                # Extract image
                image = None
                img_selectors = ["img._396cs4", "img._2r_T1I", "img._3exPp9", "img[class*='product']", "img"]
                for selector in img_selectors:
                    img = item.select_one(selector)
                    if img and img.has_attr("src"):
                        src = img.get("src")
                        if src:
                            image = src if src.startswith("http") else f"https:{src}" if src.startswith("//") else None
                            break
                
                if title and len(title.strip()) > 3:  # Only add if we have a valid title
                    results.append({
                        "title": title,
                        "link": link,
                        "image": image,
                        "price": price,
                        "rating": rating
                    })
                    
            except Exception as e:
                print(f"⚠️ Error processing item {i}: {e}")
                continue
        
        print(f"✅ Successfully scraped {len(results)} products from Flipkart")
        return results
        
    except Exception as e:
        print(f"❌ Error scraping Flipkart: {e}")
        return []

# Create a scraper object that main.py expects
class FlipkartScraper:
    def __init__(self):
        pass
    
    async def scrape(self, query: str, max_results: int = 20):
        # Run the synchronous scraper in a thread to make it async
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, scrape_flipkart, query, max_results)

scraper = FlipkartScraper()
