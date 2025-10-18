import re
import random
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEARCH_URL = "https://www.flipkart.com/search?q={}"

# Rotate real User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.flipkart.com/"
    }

def create_session():
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5,
                  status_forcelist=[429,500,502,503,504])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def scrape_flipkart(product: str, max_results: int = 20):
    session = create_session()
    url = SEARCH_URL.format(product.replace(" ", "+"))
    resp = session.get(url, headers=get_headers(), timeout=5)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    results = []
    count = 0

    # 1. Find every <div> that has both a product <a href="/…/p/…"> and a price "₹…"
    for div in soup.find_all("div"):
        link_tag = div.find("a", href=re.compile(r"/[^/]+/p/"))
        price_text = div.find(string=re.compile(r"₹[\d,]+"))
        if not link_tag or not price_text:
            continue

        # 2. Link
        href = link_tag["href"].split("?")[0]
        link = ("https://www.flipkart.com" + href
                if href.startswith("/") else href)

        # 3. Title: grid or list fallback, else link text
        title = None
        for sel in ("div._4rR01T", "a.s1Q9rs"):
            t = div.select_one(sel)
            if t and t.get_text(strip=True):
                title = t.get_text(strip=True)
                break
        if not title:
            title = link_tag.get_text(strip=True)

        # 4. Image: any valid Flipkart JPG/PNG URL
        img = div.find("img", src=re.compile(r"^https?://.*\.(?:jpg|jpeg|png)"))
        image = img["src"] if img else None

        # 5. Clean price
        price = re.search(r"₹[\d,]+", price_text).group()

        # 6. Rating (if present)
        rating_text = div.find(string=re.compile(r"\d+\.\d+\s*out of 5"))
        rating = (re.search(r"\d+\.\d+", rating_text).group()
                  if rating_text else None)

        results.append({
            "title": title,
            "link": link,
            "image": image,
            "price": price,
            "rating": rating
        })

        count += 1
        if count >= max_results:
            break

    return results