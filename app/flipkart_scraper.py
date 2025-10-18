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

def create_mock_element(element):
    """Create a mock element for consistency"""
    return type('MockElement', (), {
        'get': lambda self, key, default=None: element.get(key, default),
        'select_one': lambda self, selector: element.select_one(selector) if hasattr(element, 'select_one') else None,
        'get_text': lambda self, strip=False: element.get_text(strip=strip) if hasattr(element, 'get_text') else '',
        'select': lambda self, selector: element.select(selector) if hasattr(element, 'select') else []
    })()

def extract_from_json_data(soup, max_results):
    """Extract product data from JSON embedded in script tags"""
    items = []
    try:
        # Look for JSON data in script tags
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and ('productId' in script.string or 'productInfo' in script.string):
                script_content = script.string
                
                # Try to find product data patterns
                # Look for product objects with common fields
                patterns = [
                    r'"productId":"([^"]+)"',
                    r'"id":"([^"]+)"',
                    r'"title":"([^"]+)"',
                    r'"newTitle":"([^"]+)"',
                    r'"pricing":\{"prices":\[.*?\{"value":(\d+)\}',
                    r'"rating":\{"average":(\d+\.\d+)',
                    r'"imageUrl":"([^"]+)"',
                    r'"url":"([^"]+)"'
                ]
                
                # Extract product information using regex
                product_ids = re.findall(r'"productId":"([^"]+)"', script_content)
                titles = re.findall(r'"title":"([^"]+)"', script_content)
                prices = re.findall(r'"value":(\d+)', script_content)
                ratings = re.findall(r'"average":(\d+\.\d+)', script_content)
                images = re.findall(r'"imageUrl":"([^"]+)"', script_content)
                urls = re.findall(r'"url":"([^"]+)"', script_content)
                
                # Create mock elements from extracted data
                for i in range(min(len(product_ids), max_results)):
                    if i < len(product_ids):
                        mock_data = {
                            'productId': product_ids[i] if i < len(product_ids) else f"product_{i}",
                            'title': titles[i] if i < len(titles) else f"Product {i+1}",
                            'price': f"₹{prices[i]}" if i < len(prices) else None,
                            'rating': ratings[i] if i < len(ratings) else None,
                            'image': images[i] if i < len(images) else None,
                            'url': urls[i] if i < len(urls) else None
                        }
                        
                        # Create a mock element with the extracted data
                        mock_element = type('MockElement', (), {
                            'get': lambda self, key, default=None: mock_data.get(key, default),
                            'select_one': lambda self, selector: None,
                            'get_text': lambda self, strip=False: mock_data.get('title', ''),
                            'select': lambda self, selector: []
                        })()
                        items.append(mock_element)
                        print(f"Extracted product from JSON: {mock_data.get('title', 'Unknown')[:50]}...")
                
                if items:
                    break
                    
    except Exception as e:
        print(f"JSON extraction failed: {e}")
    
    return items

def scrape_flipkart(query: str, max_results=50):
    """
    Ultra-fast Flipkart scraper with clean data extraction:
    - Clean titles without extra text
    - Proper price extraction
    - Rating extraction
    - Image extraction
    """
    try:
        url = SEARCH_URL.format(query.replace(" ", "+"))
        
        # Create session with retry strategy
        session = create_session()
        
        # Get dynamic headers with random User-Agent
        headers = get_headers()
        
        # Ultra-fast request with very short timeout
        response = session.get(url, headers=headers, timeout=3)
        response.raise_for_status()
        
        html = response.text
        
        # Debug: Print first 2000 characters of HTML
        print(f"HTML content preview: {html[:2000]}...")

        soup = BeautifulSoup(html, "html5lib")
        
        # Debug: Look for any divs with data-id
        all_divs_with_data_id = soup.select('div[data-id]')
        print(f"Found {len(all_divs_with_data_id)} divs with data-id")
        
        # Debug: Look for any divs with product-like classes
        all_divs = soup.select('div')
        product_like_divs = []
        for div in all_divs:
            classes = div.get('class', [])
            if any('product' in str(cls).lower() or 'item' in str(cls).lower() or 'card' in str(cls).lower() or 'result' in str(cls).lower() for cls in classes):
                product_like_divs.append(div)
        print(f"Found {len(product_like_divs)} divs with product-like classes")
        
        # Debug: Print some class names we found
        if all_divs:
            sample_classes = [div.get('class', []) for div in all_divs[:10]]
            print(f"Sample classes found: {sample_classes}")
        
            results = []

        # Try multiple selectors to find products - updated for current Flipkart structure
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
            'div[class*="_2kHMtA"]',
            # New selectors for current structure
            'div[class*="_1xHGtK"]',
            'div[class*="_3liAhj"]',
            'div[class*="_2kHMtA"]',
            'div[class*="_13oc-S"]',
            'div[class*="_1fQZEK"]',
            'div[class*="_2B099V"]',
            'div[class*="_2WkVRV"]',
            'div[class*="_4rR01T"]',
            'div[class*="s1Q9rs"]',
            'div[class*="_1xHGtK"]',
            'div[class*="_3liAhj"]',
            'div[class*="_2kHMtA"]',
            # Generic product selectors
            'div[class*="product"]',
            'div[class*="item"]',
            'div[class*="card"]',
            'div[class*="result"]'
        ]
        
        items = []
        for selector in selectors_to_try:
            found_items = soup.select(selector)
            if found_items:
                print(f"Found {len(found_items)} items with selector '{selector}'")
                items.extend(found_items)
                break
        
        # If no items found with traditional selectors, try JSON extraction for widget-based layouts
        if not items:
            print("No items found with traditional selectors, trying JSON extraction...")
            items = extract_from_json_data(soup, max_results)
        
        # If still no items, try alternative approaches
        if not items:
            print("No items found with JSON extraction, trying alternative approaches...")
            
            # Try to find any links to products
            product_links = soup.select('a[href*="/p/"]')
            if product_links:
                print(f"Found {len(product_links)} product links")
                # Create mock elements from product links
                for i, link in enumerate(product_links[:max_results]):
                    mock_element = create_mock_element(link)
                    items.append(mock_element)
                    print(f"Created mock element from link {i+1}")
            
            # Try to find any divs that might contain product information
            if not items:
                all_divs = soup.select('div')
                for div in all_divs:
                    # Look for divs that might contain product info
                    div_text = div.get_text(strip=True)
                    if any(keyword in div_text.lower() for keyword in ['₹', 'price', 'rating', 'reviews']) and len(div_text) > 20:
                        mock_element = create_mock_element(div)
                        items.append(mock_element)
                        if len(items) >= max_results:
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
        
        # Clean data extraction
        for i, item in enumerate(items):
            # Handle both regular elements and mock elements
            if hasattr(item, 'get') and callable(item.get):
                product_id = item.get("data-id") or item.get("data-testid") or item.get("productId") or f"item_{i}"
            else:
                product_id = f"item_{i}"
            
            # Debug: Print item HTML structure
            print(f"Item {i+1} HTML: {str(item)[:200]}...")
            
            # Clean title extraction
            title = None
            
            # Check if this is a mock element with pre-extracted data
            if hasattr(item, 'get') and item.get('title'):
                title = item.get('title')
                print(f"Using pre-extracted title: {title[:50]}...")
            else:
                # Try traditional selectors for regular elements
                title_selectors = [
                    "div[class*='_4rR01T']",  # Main title class
                    "a[class*='s1Q9rs']",    # Alternative title class
                    "div[class*='_2WkVRV']", # Another title class
                    "div[class*='_2B099V']", # Product name class
                    "h1", "h2", "h3", "h4", "h5", "h6",  # Header tags
                    "div[class*='title']", "span[class*='title']", "a[class*='title']",
                    "div[class*='name']", "span[class*='name']", "a[class*='name']"
                ]
                
                for selector in title_selectors:
                    title_tag = item.select_one(selector)
                    if title_tag and title_tag.get_text(strip=True):
                        title_text = title_tag.get_text(strip=True)
                        # Clean up the title - remove extra text
                        if "Add to Compare" in title_text:
                            title_text = title_text.replace("Add to Compare", "").strip()
                        if "Currently unavailable" in title_text:
                            title_text = title_text.replace("Currently unavailable", "").strip()
                        # Remove rating and review text
                        title_text = re.sub(r'\d+\.\d+.*?Reviews', '', title_text)
                        title_text = re.sub(r'\d+,\d+ Ratings.*?Reviews', '', title_text)
                        # Remove price text
                        title_text = re.sub(r'₹[\d,]+', '', title_text)
                        title_text = re.sub(r'\d+% off', '', title_text)
                        title_text = re.sub(r'Only \d+ left', '', title_text)
                        title_text = re.sub(r'Upto₹[\d,]+Off on Exchange', '', title_text)
                        title_text = re.sub(r'Bank Offer', '', title_text)
                        title = title_text.strip()
                        if title:
                            print(f"Found clean title with selector '{selector}': {title[:50]}...")
                            break
            
            # Link extraction (moved before title fallback)
                link = None
            
            # Check if this is a mock element with pre-extracted data
            if hasattr(item, 'get') and item.get('url'):
                link = item.get('url')
                print(f"Using pre-extracted link: {link}")
            else:
                # Try traditional selectors for regular elements
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
            
            # Fallback: Extract title from link URL if no clean title found
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
            
            # Final fallback: Use link text as title if still no title found
            if not title:
                try:
                    # Get the link element and extract its text
                    a_tag = item.select_one("a")
                    if a_tag and a_tag.get_text(strip=True):
                        link_text = a_tag.get_text(strip=True)
                        # Clean up the link text
                        if "Add to Compare" in link_text:
                            link_text = link_text.replace("Add to Compare", "").strip()
                        if "Currently unavailable" in link_text:
                            link_text = link_text.replace("Currently unavailable", "").strip()
                        # Remove extra text using regex - more comprehensive cleaning
                        import re
                        link_text = re.sub(r'\d+\.\d+.*?Reviews', '', link_text)
                        link_text = re.sub(r'\d+,\d+ Ratings.*?Reviews', '', link_text)
                        link_text = re.sub(r'₹[\d,]+', '', link_text)
                        link_text = re.sub(r'\d+% off', '', link_text)
                        link_text = re.sub(r'Only \d+ left', '', link_text)
                        link_text = re.sub(r'Upto₹[\d,]+Off on Exchange', '', link_text)
                        link_text = re.sub(r'Bank Offer', '', link_text)
                        # Remove technical specifications
                        link_text = re.sub(r'\d+ GB ROM.*?Processor', '', link_text)
                        link_text = re.sub(r'\d+\.\d+ cm.*?Display', '', link_text)
                        link_text = re.sub(r'\d+MP.*?Camera', '', link_text)
                        link_text = re.sub(r'\d+ year warranty.*?Accessories', '', link_text)
                        link_text = re.sub(r'% off.*?Exchange', '', link_text)
                        # Clean up any remaining extra text
                        link_text = re.sub(r'\s+', ' ', link_text)  # Multiple spaces to single space
                        link_text = link_text.strip()
                        title = link_text.strip()
                        if title:
                            print(f"Extracted title from link text: {title[:50]}...")
                except:
                    pass
            
            # Clean price extraction - use regex to find price in all text
            price = None
            
            # Check if this is a mock element with pre-extracted data
            if hasattr(item, 'get') and item.get('price'):
                price = item.get('price')
                print(f"Using pre-extracted price: {price}")
            else:
                # Try traditional extraction for regular elements
                all_text = item.get_text()
                price_patterns = re.findall(r'₹[\d,]+', all_text)
                if price_patterns:
                    # Get the first price (main price)
                    price = price_patterns[0]
                    print(f"Found price using regex: {price}")
            
            # Fallback: try specific selectors if regex didn't work
            if not price:
                price_selectors = [
                    "div[class*='_30jeq3']",  # Main price class
                    "span[class*='_30jeq3']", # Price span
                    "div[class*='_1_WHN1']",  # Alternative price class
                    "span[class*='_1_WHN1']", # Price span
                    "div[class*='_25b18c']",  # Another price class
                    "span[class*='_25b18c']", # Price span
                    "div[class*='_3tbKJd']",  # Price class
                    "span[class*='_3tbKJd']", # Price span
                    # Look for price in the main container
                    "div[class*='tUxRFH'] div[class*='_30jeq3']",
                    "div[class*='tUxRFH'] span[class*='_30jeq3']",
                    "div[class*='tUxRFH'] div[class*='_1_WHN1']",
                    "div[class*='tUxRFH'] span[class*='_1_WHN1']",
                    # General price selectors
                    "div[class*='price']", "span[class*='price']"
                ]
                
                for selector in price_selectors:
                    price_tag = item.select_one(selector)
                    if price_tag and price_tag.get_text(strip=True):
                        price_text = price_tag.get_text(strip=True)
                        # Clean up price - extract just the main price
                        if '₹' in price_text:
                            # Extract the first price (main price)
                            price_match = re.search(r'₹[\d,]+', price_text)
                            if price_match:
                                price = price_match.group()
                                print(f"Found price with selector '{selector}': {price}")
                                break
            
            # Clean rating extraction - use regex to find rating in all text
            rating = None
            
            # Check if this is a mock element with pre-extracted data
            if hasattr(item, 'get') and item.get('rating'):
                rating = item.get('rating')
                print(f"Using pre-extracted rating: {rating}")
            else:
                # Try traditional extraction for regular elements
                rating_patterns = re.findall(r'\d+\.\d+', all_text)
                if rating_patterns:
                    # Get the first rating (product rating, not screen size)
                    for pattern in rating_patterns:
                        rating_val = float(pattern)
                        # Filter out screen sizes and other measurements (typically > 10)
                        if 1.0 <= rating_val <= 5.0:
                            rating = pattern
                            print(f"Found rating using regex: {rating}")
                            break
            
            # Fallback: try specific selectors if regex didn't work
            if not rating:
                rating_selectors = [
                    "div[class*='_3LWZlK']",  # Main rating class
                    "span[class*='_3LWZlK']", # Rating span
                    "div[class*='_2d4LTz']",  # Alternative rating class
                    "span[class*='_2d4LTz']", # Rating span
                    "div[class*='_3i9_wc']",  # Another rating class
                    "span[class*='_3i9_wc']", # Rating span
                    # Look for rating in the main container
                    "div[class*='tUxRFH'] div[class*='_3LWZlK']",
                    "div[class*='tUxRFH'] span[class*='_3LWZlK']",
                    "div[class*='tUxRFH'] div[class*='_2d4LTz']",
                    "div[class*='tUxRFH'] span[class*='_2d4LTz']",
                    # General rating selectors
                    "div[class*='rating']", "span[class*='rating']"
                ]
                
                for selector in rating_selectors:
                    rating_tag = item.select_one(selector)
                    if rating_tag and rating_tag.get_text(strip=True):
                        rating_text = rating_tag.get_text(strip=True)
                        # Clean up rating - extract just the rating number
                        rating_match = re.search(r'\d+\.\d+', rating_text)
                        if rating_match:
                            rating = rating_match.group()
                            print(f"Found rating with selector '{selector}': {rating}")
                            break
            
            # Image extraction
            image = None
            
            # Check if this is a mock element with pre-extracted data
            if hasattr(item, 'get') and item.get('image'):
                image = item.get('image')
                print(f"Using pre-extracted image: {image[:50]}...")
            else:
                # Try traditional selectors for regular elements
                image_selectors = [
                    "img[class*='_396cs4']",  # Main image class
                    "img[class*='_2r_T1I']",  # Alternative image class
                    "img[class*='_3exPp9']",  # Another image class
                    "img[class*='_1BweB8']",  # Image class
                    "img[class*='_2mylT6']",  # Image class
                    "img[class*='_396cs4']",  # Main product image
                    "img[src*='flipkart']",   # Any Flipkart image
                    "img"  # Any image as fallback
                ]
                
                for selector in image_selectors:
                    img_tag = item.select_one(selector)
                    if img_tag and img_tag.get("src"):
                        image = img_tag.get("src")
                        # Make sure it's a full URL
                        if image.startswith("//"):
                            image = "https:" + image
                        elif image.startswith("/"):
                            image = "https://www.flipkart.com" + image
                        print(f"Found image with selector '{selector}': {image[:50]}...")
                        break
            
            # Debug: Print what we found
            print(f"Product {i+1}: ID={product_id}, Title={title[:30] if title else 'None'}..., Price={price}, Rating={rating}, Image={image[:30] if image else 'None'}...")
            
            # Only add if we have essential data (relaxed requirements)
            if title:  # Only require title, not product_id
                results.append({
                    "id": product_id,
                    "title": title,
                    "link": link,
                    "image": image,
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