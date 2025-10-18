import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEARCH_URL = "https://www.flipkart.com/search?q={}"

# Multiple User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
]

def get_headers():
    """Get random headers with User-Agent rotation"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.flipkart.com/"
    }

def create_session():
    """Create a session with retry strategy"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def scrape_flipkart(query: str, max_results: int = 20):
    """
    Scrape Flipkart products using requests (no Playwright)
    """
    try:
        session = create_session()
        url = SEARCH_URL.format(query.replace(' ', '+'))
        
        print(f"🔍 Scraping Flipkart for: {query}")
        
        response = session.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, "html5lib")
        
        # Try multiple selectors for different page layouts
        product_selectors = [
            "div._13oc-S",  # Traditional grid layout
            "div[data-id]",  # Generic data-id selector
            "div._1AtVbE",  # Alternative layout
            "div._2kHMtA"   # Another layout
        ]
        
        products = []
        for selector in product_selectors:
            products = soup.select(selector)
            if products:
                print(f"✅ Found {len(products)} products with selector: {selector}")
                break
        
        if not products:
            print("❌ No products found with any selector")
            return []
        
        results = []
        for i, product in enumerate(products[:max_results]):
            try:
                # Extract link
                link = None
                a_tag = product.select_one("a._1fQZEK") or product.select_one("a.s1Q9rs") or product.select_one("a[href*='/p/']")
                if a_tag:
                    href = a_tag.get("href")
                    if href:
                        if href.startswith("http"):
                            link = href.split("?")[0]
                        else:
                            link = "https://www.flipkart.com" + href.split("?")[0]
                
                # Extract title
                title = None
                title_selectors = ["div._4rR01T", "a.s1Q9rs", "div._2WkVRV", "span.B_NuCI"]
                for selector in title_selectors:
                    title_tag = product.select_one(selector)
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        break
                
                # If no title found, try to extract from link text
                if not title and a_tag:
                    title = a_tag.get_text(strip=True)
                
                # Extract price using regex as primary method
                price = None
                price_text = product.get_text()
                price_match = re.search(r'₹[\d,]+', price_text)
                if price_match:
                    price = price_match.group()
                else:
                    # Fallback to CSS selectors
                    price_selectors = ["div._30jeq3", "div._1vC4OE", "span._2-ut7f"]
                    for selector in price_selectors:
                        price_tag = product.select_one(selector)
                        if price_tag:
                            price = price_tag.get_text(strip=True)
                            break
                
                # Extract rating using regex as primary method
                rating = None
                rating_match = re.search(r'(\d+\.\d+)', price_text)
                if rating_match:
                    rating_val = float(rating_match.group(1))
                    if 1.0 <= rating_val <= 5.0:  # Filter for valid ratings
                        rating = str(rating_val)
                
                if not rating:
                    # Fallback to CSS selectors
                    rating_selectors = ["div._3LWZlK", "span._2_KrJI", "div._3i9_wc"]
                    for selector in rating_selectors:
                        rating_tag = product.select_one(selector)
                        if rating_tag:
                            rating_text = rating_tag.get_text(strip=True)
                            rating_match = re.search(r'(\d+\.\d+)', rating_text)
                            if rating_match:
                                rating_val = float(rating_match.group(1))
                                if 1.0 <= rating_val <= 5.0:
                                    rating = str(rating_val)
                                    break
                
                # Extract image
                image = None
                img_tag = product.select_one("img._396cs4") or product.select_one("img._2r_T1I") or product.select_one("img")
                if img_tag:
                    image = img_tag.get("src")
                    if image and image.startswith("//"):
                        image = "https:" + image
                
                if title:  # Only add if we have at least a title
                    results.append({
                        "title": title,
                        "link": link,
                        "image": image,
                        "price": price,
                        "rating": rating
                    })
                    
            except Exception as e:
                print(f"⚠️ Error processing product {i}: {e}")
                continue
        
        print(f"✅ Successfully scraped {len(results)} products from Flipkart")
        return results
        
    except Exception as e:
        print(f"❌ Error scraping Flipkart: {e}")
        return []


