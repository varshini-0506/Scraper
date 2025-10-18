# flipkart_scraper_clean.py
import time
import random
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEARCH_URL = "https://www.flipkart.com/search?q={}"

USER_AGENTS = [
    # rotate UA to reduce chance of different mobile/desktop markup
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.flipkart.com/"
    }

def create_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.6, status_forcelist=[429,500,502,503,504], allowed_methods=frozenset(["GET"]))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s

def _extract_image_src(tag) -> Optional[str]:
    """Return the best image URL or None. Do NOT return placeholders."""
    if not tag:
        return None
    # common attributes where Flipkart keeps images
    for attr in ("data-src", "data-image", "data-srcset", "src", "data-original", "data-hires"):
        val = tag.get(attr)
        if val:
            # if srcset-like, pick the first URL
            if "," in val:
                first = val.split(",")[0].strip().split(" ")[0]
                if first.startswith("//"):
                    return "https:" + first
                return first
            if val.startswith("//"):
                return "https:" + val
            return val
    # try srcset explicitly
    srcset = tag.get("srcset") or ""
    if srcset:
        first = srcset.split(",")[0].strip().split(" ")[0]
        if first.startswith("//"):
            return "https:" + first
        return first
    return None

def _first_reasonable_text(text: str, min_len=6, max_len=220) -> Optional[str]:
    parts = [p.strip() for p in re.split(r'[\n\r|–\-•]+', text) if p.strip()]
    for p in parts:
        if min_len <= len(p) <= max_len:
            return p
    return None

def scrape_flipkart(query: str, max_results: int = 20, verbose: bool = False) -> List[Dict]:
    session = create_session()
    # Preflight to obtain cookies (ignore errors)
    try:
        session.get("https://www.flipkart.com", headers=get_headers(), timeout=8)
    except Exception:
        pass

    url = SEARCH_URL.format(quote_plus(query))
    time.sleep(random.uniform(0.2, 0.7))
    resp = session.get(url, headers=get_headers(), timeout=12)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # candidate container selectors
    container_selectors = [
        "div._13oc-S",     # common grid container
        "div[data-id]",    # generic product cards (your logs found this)
        "div._1AtVbE",     # alternate
        "div._2kHMtA",     # product card
        "a.s1Q9rs",        # some small card anchors (used for mobiles)
        "div._3liAhj",     # other layouts
        "div._2kSfQ4"      # sometimes used
    ]

    candidates = []
    for sel in container_selectors:
        found = soup.select(sel)
        if found:
            candidates = found
            if verbose:
                print(f"Found {len(found)} candidates with selector: {sel}")
            break

    # anchor fallback (links to /p/)
    if not candidates:
        anchors = soup.find_all("a", href=re.compile(r"/p/"))
        seen = set()
        for a in anchors:
            href = a.get("href")
            if not href:
                continue
            key = href.split("?")[0]
            if key in seen:
                continue
            seen.add(key)
            candidates.append(a)
        if verbose:
            print(f"Fallback anchors found: {len(candidates)}")

    results = []
    # selectors to try for each field (multiple fallbacks)
    title_selectors = ["div._4rR01T", "a.s1Q9rs", "a.IRpwTa", "div._2WkVRV", "span.B_NuCI", "div._3wU53n"]
    price_selectors = ["div._30jeq3", "div._1vC4OE", "div._25b18c", "span._2-ut7f"]
    rating_selectors = ["div._3LWZlK", "span._2_KrJI", "div._3i9_wc"]

    for idx, card in enumerate(candidates):
        if len(results) >= max_results:
            break

        try:
            # try to find an anchor to product page
            a_tag = None
            if card.name == "a" and card.get("href") and re.search(r"/p/", card.get("href")):
                a_tag = card
            else:
                a_tag = card.select_one("a[href*='/p/']") or card.find("a")

            link = None
            if a_tag:
                href = a_tag.get("href")
                if href:
                    href = href.split("?")[0]
                    if href.startswith("http"):
                        link = href
                    else:
                        link = "https://www.flipkart.com" + href

            # TITLE: many fallbacks (keep None if not found)
            title = None
            for ts in title_selectors:
                t = card.select_one(ts)
                if t and t.get_text(strip=True):
                    title = t.get_text(strip=True)
                    break
            if not title and a_tag:
                # anchor title attribute / direct anchor text
                title = (a_tag.get("title") or a_tag.get_text(strip=True)) or None
            if not title:
                # try image alt
                img_for_title = card.select_one("img") or (a_tag.select_one("img") if a_tag else None)
                if img_for_title:
                    title = img_for_title.get("alt") or img_for_title.get("title")
            if not title:
                # fallback: first reasonable chunk of text in card
                txt = card.get_text(" ", strip=True)
                title = _first_reasonable_text(txt)

            # PRICE
            price = None
            for ps in price_selectors:
                ptag = card.select_one(ps)
                if ptag:
                    ptxt = ptag.get_text(strip=True)
                    if ptxt:
                        price = ptxt
                        break
            # regex fallback (if price shown elsewhere)
            if not price:
                all_text = card.get_text(" ", strip=True)
                m = re.search(r'₹\s?[\d,]+(?:\.\d{1,2})?', all_text)
                if m:
                    price = m.group().replace(" ", "")

            # RATING
            rating = None
            for rs in rating_selectors:
                rtag = card.select_one(rs)
                if rtag:
                    rtxt = rtag.get_text(strip=True)
                    rm = re.search(r'(\d+(?:\.\d+)?)', rtxt)
                    if rm:
                        rating = rm.group(1)
                        break
            if not rating:
                # sometimes rating appears near review counts e.g. "4.3 ★ | 1,234 Ratings"
                m = re.search(r'(\d+(?:\.\d+)?)\s*(?:★|Ratings|Rating)', card.get_text(" ", strip=True), re.I)
                if m:
                    rating = m.group(1)

            # IMAGE
            img_tag = None
            if a_tag:
                img_tag = a_tag.select_one("img")
            if not img_tag:
                img_tag = card.select_one("img")
            image = _extract_image_src(img_tag)

            # Build the result: only actual scraped values or None (no static defaults)
            item = {
                "title": title if title else None,
                "link": link if link else None,
                "image": image if image else None,
                "price": price if price else None,
                "rating": rating if rating else None
            }

            # if there's no title and no link, skip — it's not a product
            if not item["title"] and not item["link"]:
                if verbose:
                    print(f"Skipping candidate #{idx}: no title and no link")
                continue

            # append result (even if some fields are None — we do NOT insert defaults)
            results.append(item)

            if verbose:
                found = [k for k,v in item.items() if v is not None]
                missing = [k for k,v in item.items() if v is None]
                print(f"Candidate #{idx} -> found: {found} | missing: {missing}")

        except Exception as e:
            if verbose:
                print(f"Error processing candidate #{idx}: {e}")
            continue

    if verbose:
        print(f"Scraped {len(results)} items for query={query}")

    return results


