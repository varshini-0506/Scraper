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
    if not tag:
        return None
    for attr in ("data-src", "data-image", "data-srcset", "src", "data-original", "data-hires"):
        val = tag.get(attr)
        if val:
            if "," in val:
                first = val.split(",")[0].strip().split(" ")[0]
                if first.startswith("//"):
                    return "https:" + first
                return first
            if val.startswith("//"):
                return "https:" + val
            return val
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

def _clean_title(raw: str) -> Optional[str]:
    """Clean large concatenated card text into a sane title or None."""
    if not raw:
        return None
    s = raw.strip()
    # remove common prefix
    s = re.sub(r'^\s*Add to Compare\s*', '', s, flags=re.I)
    # cut off from price marker onward (₹ usually marks start of price/offer junk)
    if "₹" in s:
        s = s.split("₹", 1)[0]
    # remove 'xx Ratings' and 'xx Reviews' blocks
    s = re.sub(r'\d[\d,]*\s*Ratings?', '', s, flags=re.I)
    s = re.sub(r'\d[\d,]*\s*Reviews?', '', s, flags=re.I)
    # remove phrases like "Upto..." / "Off on Exchange" etc (a conservative approach)
    s = re.split(r'Upto|Off on|Bank Offer|Only few left|In the box|Warranty|Warranty for', s, maxsplit=1, flags=re.I)[0]
    # collapse whitespace
    s = re.sub(r'\s{2,}', ' ', s).strip()
    # if still too long, take first sentence / chunk
    if len(s) > 180:
        s = s[:180].rsplit(' ', 1)[0]  # avoid cutting mid-word
    return s if s else None

def _extract_rating(card, a_tag=None) -> Optional[str]:
    """
    Extract rating as a single-digit or single-digit-with-decimal like '4' or '4.6'.
    Avoid capturing review counts (which are large integers with commas).
    """
    # 1) common Flipkart rating element (e.g. div._3LWZlK)
    rating_selectors = ["div._3LWZlK", "span._2_KrJI"]
    for sel in rating_selectors:
        r = card.select_one(sel)
        if r:
            txt = r.get_text(strip=True)
            # only accept patterns like 4 or 4.6 or 4.61 (limit decimals to at most 2)
            m = re.match(r'^[0-5](?:\.[0-9]{1,2})?$', txt)
            if m:
                return m.group(0)
    # 2) look for 'x.x ★' or 'x.x out of 5' near the card text
    full = card.get_text(" ", strip=True)
    m = re.search(r'([0-5](?:\.[0-9]{1,2})?)\s*(?:★|out of 5|/5)', full, flags=re.I)
    if m:
        return m.group(1)
    # 3) sometimes rating sits inside the anchor or adjacent small text, try a_tag
    if a_tag:
        a_text = a_tag.get_text(" ", strip=True)
        m = re.search(r'([0-5](?:\.[0-9]{1,2})?)\s*(?:★|out of 5|/5)', a_text, flags=re.I)
        if m:
            return m.group(1)
    # If nothing reliable found, return None (do NOT return big ints)
    return None

def scrape_flipkart(query: str, max_results: int = 20, verbose: bool = False) -> List[Dict]:
    session = create_session()
    try:
        session.get("https://www.flipkart.com", headers=get_headers(), timeout=6)
    except Exception:
        pass

    url = SEARCH_URL.format(quote_plus(query))
    time.sleep(random.uniform(0.2, 0.7))
    resp = session.get(url, headers=get_headers(), timeout=12)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    container_selectors = [
        "div._13oc-S", "div[data-id]", "div._1AtVbE", "div._2kHMtA",
        "a.s1Q9rs", "div._3liAhj", "div._2kSfQ4"
    ]

    candidates = []
    for sel in container_selectors:
        found = soup.select(sel)
        if found:
            candidates = found
            if verbose:
                print(f"Found {len(found)} candidates with selector: {sel}")
            break

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
    title_selectors = ["div._4rR01T", "a.s1Q9rs", "a.IRpwTa", "div._2WkVRV", "span.B_NuCI", "div._3wU53n"]
    price_selectors = ["div._30jeq3", "div._1vC4OE", "div._25b18c", "span._2-ut7f"]

    for idx, card in enumerate(candidates):
        if len(results) >= max_results:
            break
        try:
            # find anchor
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

            # TITLE: prefer strict selectors; only fallback to big text when necessary, then CLEAN it
            title = None
            for ts in title_selectors:
                t = card.select_one(ts)
                if t and t.get_text(strip=True):
                    title = t.get_text(strip=True)
                    break
            if not title and a_tag:
                # try anchor title attribute
                title = (a_tag.get("title") or a_tag.get_text(strip=True)) or None

            if not title:
                # fallback to first reasonable chunk and then clean
                raw = card.get_text(" ", strip=True)
                candidate_title = _first_reasonable_text(raw)
                title = _clean_title(candidate_title or raw)

            # PRICE
            price = None
            for ps in price_selectors:
                ptag = card.select_one(ps)
                if ptag:
                    ptxt = ptag.get_text(strip=True)
                    if ptxt:
                        price = ptxt
                        break
            if not price:
                allt = card.get_text(" ", strip=True)
                m = re.search(r'₹\s?[\d,]+(?:\.\d{1,2})?', allt)
                if m:
                    price = m.group().replace(" ", "")

            # RATING (robust)
            rating = _extract_rating(card, a_tag=a_tag)

            # IMAGE
            img_tag = None
            if a_tag:
                img_tag = a_tag.select_one("img")
            if not img_tag:
                img_tag = card.select_one("img")
            image = _extract_image_src(img_tag)

            item = {
                "title": title if title else None,
                "link": link if link else None,
                "image": image if image else None,
                "price": price if price else None,
                "rating": rating if rating else None
            }

            # skip if no title and no link
            if not item["title"] and not item["link"]:
                if verbose:
                    print(f"Skipping candidate #{idx}: no title and no link")
                continue

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

