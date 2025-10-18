import requests
from bs4 import BeautifulSoup
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEARCH_URL = "https://www.amazon.in/s?k={}"

# Comprehensive headers to mimic a real browser and reduce blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
    "Referer": "https://www.amazon.in/"
}

def create_session():
    """Create a session with retry strategy"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
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
        time.sleep(random.uniform(0.5, 2.0))
        
        # 10-second timeout to prevent hanging
        response = session.get(url, headers=HEADERS, timeout=10)
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
        
        soup = BeautifulSoup(html, "lxml")
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
        return {"error": "Request timed out after 10 seconds"}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection failed - Amazon may be blocking requests"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
