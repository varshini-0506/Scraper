import requests
from bs4 import BeautifulSoup
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEARCH_URL = "https://www.amazon.in/s?k={}"

# Multiple User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
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
        "Origin": "https://www.amazon.in"
    }

def create_session():
    """Create a session with retry strategy"""
    session = requests.Session()
    
    # Configure retry strategy with more conservative settings for Vercel
    retry_strategy = Retry(
        total=2,  # Reduced from 3 to avoid too many retries
        backoff_factor=2,  # Increased backoff factor
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False  # Don't raise on status codes
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def fast_scrape_amazon_products(query: str, max_results=50):
    """
    Fast Amazon product scraper with comprehensive features:
    - 10-second timeout to prevent hanging
    - CAPTCHA/block detection with multiple keywords
    - Result limit for rapid response
    - Selective extraction with robust CSS selectors
    - Comprehensive headers to reduce blocking
    """
    try:
        url = SEARCH_URL.format(query.replace(" ", "+"))
        
        # Create session with retry strategy
        session = create_session()
        
        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        try:
            # Try with longer timeout first
            response = session.get(url, headers=get_headers(), timeout=30)
            if response.status_code == 503:
                print("❌ Got 503 error, trying with different approach...")
                # Try with different headers and shorter timeout
                headers = get_headers()
                headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
                response = session.get(url, headers=headers, timeout=15)
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
        
        html = response.text
        
        # Comprehensive CAPTCHA/block detection
        block_indicators = [
            "validateCaptcha",
            "Enter the characters you see below",
            "api-services-support@amazon.in",
            "To discuss automated access to Amazon data please contact",
            "Robot Check",
            "captcha",
            "blocked",
            "access denied",
            "unusual traffic",
            "security check"
        ]
        
        if any(indicator.lower() in html.lower() for indicator in block_indicators):
            return {"error": "Blocked by Amazon - CAPTCHA or rate limiting detected"}
        
        soup = BeautifulSoup(html, "html5lib")
        results = []
        
        # Multiple selectors to capture ALL product types from Amazon results
        product_selectors = [
            'div.s-result-item[data-asin]',  # Standard product cards
            'div[data-asin]',                # Any div with ASIN
            'div[data-component-type="s-search-result"]',  # Search result components
            'div.sg-col-inner',             # Grid items
            'div[data-index]',              # Indexed items
            'div[data-cel-widget*="search_result"]'  # Search result widgets
        ]
        
        all_items = []
        for selector in product_selectors:
            items = soup.select(selector)
            all_items.extend(items)
        
        # Remove duplicates based on data-asin
        seen_asins = set()
        unique_items = []
        for item in all_items:
            asin = item.get("data-asin")
            if asin and asin not in seen_asins:
                seen_asins.add(asin)
                unique_items.append(item)
        
        print(f"Found {len(unique_items)} unique products on the page")
        
        for item in unique_items:
            asin = item.get("data-asin")
            if not asin:
                continue
                
            # Title extraction with comprehensive fallbacks
            title_tag = None
            title_selectors = [
                "h2 a.a-link-normal.s-underline-text",
                "h2 a span",
                "h2 span",
                "h2 a",
                "h2",
                "a span[data-component-type='s-product-image']",
                ".s-size-mini .s-color-base",
                "span[data-component-type='s-product-image']",
                "a[data-component-type='s-product-image']"
            ]
            
            for selector in title_selectors:
                title_tag = item.select_one(selector)
                if title_tag and title_tag.get_text(strip=True):
                    break
            
            title = title_tag.get_text(strip=True) if title_tag else None
            
            # Link extraction with comprehensive fallback selectors
            link_tag = None
            link_selectors = [
                "h2 a.a-link-normal.s-underline-text",
                "h2 a.a-link-normal", 
                "h2 a",
                "a[href*='/dp/']",
                "a[href*='/gp/product/']",
                "a[data-asin]",
                "a[href*='amazon.in']"
            ]
            
            for selector in link_selectors:
                link_tag = item.select_one(selector)
                if link_tag and link_tag.has_attr("href"):
                    break
            
            if link_tag and link_tag.has_attr("href"):
                href = link_tag["href"]
                # Clean up the href (remove query parameters that might cause issues)
                if "?" in href:
                    href = href.split("?")[0]
                
                # Handle relative URLs
                if href.startswith("/"):
                    link = "https://www.amazon.in" + href
                elif href.startswith("http"):
                    link = href
                else:
                    link = "https://www.amazon.in/" + href
            else:
                # Fallback: construct link from ASIN if no link found
                if asin:
                    link = f"https://www.amazon.in/dp/{asin}"
                else:
                    link = None
            
            # Image - robust selector
            image_tag = (item.select_one("img.s-image") or 
                        item.select_one("img[data-src]") or 
                        item.select_one("img"))
            image = (image_tag.get('src') or image_tag.get('data-src') 
                    if image_tag else None)
            
            # Price extraction with comprehensive fallbacks
            price_tag = None
            price_selectors = [
                "span.a-price > span.a-offscreen",
                "span.a-price-whole",
                ".a-price .a-offscreen",
                "span.a-price",
                ".a-price-range",
                "span[data-a-price]",
                ".a-price-symbol",
                "span[class*='price']"
            ]
            
            for selector in price_selectors:
                price_tag = item.select_one(selector)
                if price_tag and price_tag.get_text(strip=True):
                    break
            
            price = price_tag.get_text(strip=True) if price_tag else None
            
            # Rating extraction with comprehensive fallbacks
            rating_tag = None
            rating_selectors = [
                "span.a-icon-alt",
                ".a-icon-star-small",
                "[data-rating]",
                "span[aria-label*='stars']",
                ".a-icon-star",
                "span[class*='rating']",
                "i[class*='star']"
            ]
            
            for selector in rating_selectors:
                rating_tag = item.select_one(selector)
                if rating_tag and rating_tag.get_text(strip=True):
                    break
            
            rating = rating_tag.get_text(strip=True) if rating_tag else None
            
            # Debug: Print what we found for each product
            print(f"Product {len(results)+1}: ASIN={asin}, Title={title[:50] if title else 'None'}...")
            
            # Only add if we have essential data (title and ASIN)
            if title and asin:
                results.append({
                    "asin": asin,
                    "title": title,
                    "link": link,
                    "image": image,
                    "price": price,
                    "rating": rating
                })
                
                # Result limit for rapid response
                if len(results) >= max_results:
                    break
            else:
                print(f"Skipped product: ASIN={asin}, Title={title}")
        
        print(f"Successfully scraped {len(results)} products out of {len(unique_items)} found on page")
        return results
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return [{"title": f"{query} - Product not available", "link": "https://www.amazon.in", "image": None, "price": "Price not available", "rating": None}]
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - Amazon may be blocking requests")
        return [{"title": f"{query} - Product not available", "link": "https://www.amazon.in", "image": None, "price": "Price not available", "rating": None}]
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error: {e.response.status_code}")
        return [{"title": f"{query} - Product not available", "link": "https://www.amazon.in", "image": None, "price": "Price not available", "rating": None}]
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return [{"title": f"{query} - Product not available", "link": "https://www.amazon.in", "image": None, "price": "Price not available", "rating": None}]
