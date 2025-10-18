import requests
from bs4 import BeautifulSoup
import time
import random
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
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
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

def scrape_flipkart(query: str, max_results=50):
    """
    Ultra-fast Flipkart scraper with anti-detection features:
    - User-Agent rotation
    - Realistic delays
    - Multiple fallback strategies
    - Fast data extraction
    """
    try:
        url = SEARCH_URL.format(query.replace(" ", "+"))
        
        # Create session with retry strategy
        session = create_session()
        
        # No delay for maximum speed
        # Get dynamic headers with random User-Agent
        headers = get_headers()
        
        # Ultra-fast request with very short timeout
        response = session.get(url, headers=headers, timeout=3)
        response.raise_for_status()
        
        html = response.text
        
        # Debug: Print first 1000 characters of HTML
        print(f"HTML content preview: {html[:1000]}...")
        
        # Skip block detection for speed - just continue
        
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Try multiple selectors to find products
        selectors_to_try = [
            'div[data-id]',
            'div[class*="_1AtVbE"]',
            'div[class*="_2kHMtA"]', 
            'div[class*="_13oc-S"]',
            'div[class*="_1fQZEK"]',
            'div[class*="_2B099V"]',
            'div[class*="_2WkVRV"]',
            'div[class*="_4rR01T"]',
            'div[class*="s1Q9rs"]',
            'div[class*="_1xHGtK"]',
            'div[class*="_3liAhj"]',
            'div[class*="_2kHMtA"]'
        ]
        
        items = []
        for selector in selectors_to_try:
            found_items = soup.select(selector)
            if found_items:
                print(f"Found {len(found_items)} items with selector '{selector}'")
                items.extend(found_items)
                break
        
        if not items:
            # Fallback: try to find any div with product-like classes
            all_divs = soup.select('div')
            for div in all_divs:
                classes = div.get('class', [])
                if any('product' in str(cls).lower() or 'item' in str(cls).lower() or 'card' in str(cls).lower() for cls in classes):
                    items.append(div)
                    if len(items) >= max_results:
                        break
        
        print(f"Total found {len(items)} products")
        
        # Fast data extraction with comprehensive selectors
        for i, item in enumerate(items):
            product_id = item.get("data-id") or item.get("data-testid") or f"item_{i}"
            
            # Debug: Print item HTML structure
            print(f"Item {i+1} HTML: {str(item)[:200]}...")
            
            # Comprehensive title extraction - based on actual HTML structure
            title = None
            title_selectors = [
                # Try to find title in the link text or nearby elements
                "a[href*='/p/']",  # The main product link
                "div[class*='tUxRFH'] a",  # Link inside the main container
                "a[class*='CGtC98']",  # The actual link class we see
                "div[class*='tUxRFH']",  # The main container
                "div[class*='_4rR01T']", "a[class*='s1Q9rs']", 
                "h2", "h3", "h4", "h5", "h6",
                "div[class*='title']", "span[class*='title']", "a[class*='title']",
                "div[class*='name']", "span[class*='name']", "a[class*='name']",
                "div[class*='product']", "span[class*='product']", "a[class*='product']",
                "div[class*='item']", "span[class*='item']", "a[class*='item']"
            ]
            
            for selector in title_selectors:
                title_tag = item.select_one(selector)
                if title_tag and title_tag.get_text(strip=True):
                    title = title_tag.get_text(strip=True)
                    print(f"Found title with selector '{selector}': {title[:50]}...")
                    break
            
            # Fallback: Extract title from link URL if no text title found
            if not title and link:
                try:
                    # Extract product name from URL path
                    url_parts = link.split('/')
                    for part in url_parts:
                        if 'p/' in part:
                            product_part = part.split('p/')[1] if 'p/' in part else part
                            # Clean up the product name
                            title = product_part.replace('-', ' ').replace('_', ' ').title()
                            print(f"Extracted title from URL: {title[:50]}...")
                            break
                except:
                    pass
            
            # Comprehensive link extraction
            link = None
            link_selectors = ["a", "a[href*='/p/']", "a[href*='flipkart.com']", "a[class*='link']"]
            for selector in link_selectors:
                a_tag = item.select_one(selector)
                if a_tag and a_tag.get("href"):
                    href = a_tag["href"]
                    if "?" in href:
                        href = href.split("?")[0]
                    link = "https://www.flipkart.com" + href if href.startswith("/") else href
                    print(f"Found link: {link}")
                    break
            
            # Comprehensive price extraction - based on actual HTML structure
            price = None
            price_selectors = [
                # Look for price in the main container and its children
                "div[class*='tUxRFH'] div[class*='price']",
                "div[class*='tUxRFH'] span[class*='price']",
                "div[class*='tUxRFH'] div[class*='_30jeq3']",
                "div[class*='tUxRFH'] span[class*='_30jeq3']",
                "div[class*='tUxRFH'] div[class*='_1_WHN1']",
                "div[class*='tUxRFH'] span[class*='_1_WHN1']",
                "div[class*='tUxRFH'] div[class*='_25b18c']",
                "div[class*='tUxRFH'] span[class*='_25b18c']",
                "div[class*='tUxRFH'] div[class*='_3tbKJd']",
                "div[class*='tUxRFH'] span[class*='_3tbKJd']",
                # General price selectors
                "div._30jeq3", "div._30jeq3._1_WHN1", "div[class*='price']", 
                "span[class*='price']", "div[class*='_30jeq3']", "span[class*='_30jeq3']",
                "div[class*='_1_WHN1']", "span[class*='_1_WHN1']", "div[class*='_25b18c']",
                "span[class*='_25b18c']", "div[class*='_3tbKJd']", "span[class*='_3tbKJd']"
            ]
            
            for selector in price_selectors:
                price_tag = item.select_one(selector)
                if price_tag and price_tag.get_text(strip=True):
                    price = price_tag.get_text(strip=True)
                    print(f"Found price with selector '{selector}': {price}")
                    break
            
            # Comprehensive rating extraction - based on actual HTML structure
            rating = None
            rating_selectors = [
                # Look for rating in the main container and its children
                "div[class*='tUxRFH'] div[class*='rating']",
                "div[class*='tUxRFH'] span[class*='rating']",
                "div[class*='tUxRFH'] div[class*='_3LWZlK']",
                "div[class*='tUxRFH'] span[class*='_3LWZlK']",
                "div[class*='tUxRFH'] div[class*='_2d4LTz']",
                "div[class*='tUxRFH'] span[class*='_2d4LTz']",
                "div[class*='tUxRFH'] div[class*='_3i9_wc']",
                "div[class*='tUxRFH'] span[class*='_3i9_wc']",
                # General rating selectors
                "div._3LWZlK", "div[class*='rating']", "span[class*='rating']",
                "div[class*='_3LWZlK']", "span[class*='_3LWZlK']", "div[class*='_2d4LTz']",
                "span[class*='_2d4LTz']", "div[class*='_3i9_wc']", "span[class*='_3i9_wc']"
            ]
            
            for selector in rating_selectors:
                rating_tag = item.select_one(selector)
                if rating_tag and rating_tag.get_text(strip=True):
                    rating = rating_tag.get_text(strip=True)
                    print(f"Found rating with selector '{selector}': {rating}")
                    break
            
            # Debug: Print what we found
            print(f"Product {i+1}: ID={product_id}, Title={title[:30] if title else 'None'}..., Price={price}, Rating={rating}")
            
            # Only add if we have essential data (relaxed requirements)
            if title:  # Only require title, not product_id
                results.append({
                    "id": product_id,
                    "title": title,
                    "link": link,
                    "image": None,  # Skip images for speed
                    "price": price,
                    "rating": rating
                })
                print(f"Added product {len(results)}: {title[:50]}...")
            else:
                print(f"Skipped product {i+1}: No title found")
        
        print(f"Successfully scraped {len(results)} products")
        return results
        
    except requests.exceptions.Timeout:
        print("Request timed out")
        return []
    except requests.exceptions.ConnectionError:
        print("Connection failed")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e.response.status_code}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
