# app/flipkart_scraper.py
import os
import time
import random
import re
import traceback
from typing import List, Dict, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEARCH_URL = "https://www.flipkart.com/search?q={}"

# Defaults can be overridden via env vars
DEFAULT_READ_TIMEOUT = int(os.getenv("SCRAPER_READ_TIMEOUT", "30"))  # read timeout in seconds
DEFAULT_CONNECT_TIMEOUT = int(os.getenv("SCRAPER_CONNECT_TIMEOUT", "5"))  # connect timeout in seconds
DEFAULT_MAX_RETRIES = int(os.getenv("SCRAPER_MAX_RETRIES", "4"))
DEFAULT_BACKOFF = float(os.getenv("SCRAPER_BACKOFF", "1.0"))

USER_AGENTS = [
    os.getenv("SCRAPER_UA", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")
]


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.flipkart.com/"
    }


def create_session(max_retries: int = DEFAULT_MAX_RETRIES, backoff_factor: float = DEFAULT_BACKOFF) -> requests.Session:
    """
    Create a requests Session with urllib3 Retry policy mounted.
    """
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST"])
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _get_proxies_from_env() -> Optional[dict]:
    http_p = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_p = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    if http_p or https_p:
        return {"http": http_p, "https": https_p}
    return None


def fetch_search_html(query: str, attempts: int = 3, connect_timeout: int = DEFAULT_CONNECT_TIMEOUT, read_timeout: int = DEFAULT_READ_TIMEOUT) -> str:
    """
    Fetch the search page HTML with robust attempts, exponential backoff, and optional proxy support.
    Raises requests.exceptions.RequestException on final failure.
    """
    session = create_session()
    proxies = _get_proxies_from_env()
    url = SEARCH_URL.format(quote_plus(query))

    for attempt in range(1, attempts + 1):
        try:
            # connect/read timeout tuple
            resp = session.get(url, headers=get_headers(), timeout=(connect_timeout, read_timeout), proxies=proxies)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as e:
            # print concise error and then decide whether to retry
            print(f"[scraper] fetch attempt {attempt}/{attempts} failed: {e}")
            traceback.print_exc()
            if attempt == attempts:
                # re-raise the final exception so caller (FastAPI) can return proper 502
                raise
            # exponential backoff with jitter
            sleep_for = (2 ** (attempt - 1)) * backoff_jitter()
            print(f"[scraper] sleeping for {sleep_for:.2f}s before retry...")
            time.sleep(sleep_for)
    # should never get here
    raise RuntimeError("fetch_search_html: exceeded attempts unexpectedly")


def backoff_jitter() -> float:
    """Return jitter multiplier for backoff; keeps things less synchronized."""
    return DEFAULT_BACKOFF + random.random() * 0.5


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
    if not raw:
        return None
    s = raw.strip()
    s = re.sub(r'^\s*Add to Compare\s*', '', s, flags=re.I)
    if "₹" in s:
        s = s.split("₹", 1)[0]
    s = re.sub(r'\d[\d,]*\s*Ratings?', '', s, flags=re.I)
    s = re.sub(r'\d[\d,]*\s*Reviews?', '', s, flags=re.I)
    s = re.split(r'Upto|Off on|Bank Offer|Only few left|In the box|Warranty|Warranty for', s, maxsplit=1, flags=re.I)[0]
    s = re.sub(r'\s{2,}', ' ', s).strip()
    if len(s) > 180:
        s = s[:180].rsplit(' ', 1)[0]
    return s if s else None


def _extract_rating(card, a_tag=None) -> Optional[str]:
    # prefer strict rating selectors
    rating_selectors = ["div._3LWZlK", "span._2_KrJI"]
    for sel in rating_selectors:
        r = card.select_one(sel)
        if r:
            txt = r.get_text(strip=True)
            m = re.match(r'^[0-5](?:\.[0-9]{1,2})?$', txt)
            if m:
                return m.group(0)
    full = card.get_text(" ", strip=True)
    m = re.search(r'([0-5](?:\.[0-9]{1,2})?)\s*(?:★|out of 5|/5)', full, flags=re.I)
    if m:
        return m.group(1)
    if a_tag:
        a_text = a_tag.get_text(" ", strip=True)
        m = re.search(r'([0-5](?:\.[0-9]{1,2})?)\s*(?:★|out of 5|/5)', a_text, flags=re.I)
        if m:
            return m.group(1)
    return None


def scrape_flipkart(query: str, max_results: int = 20, verbose: bool = False) -> List[Dict]:
    """
    High-level scraper: fetches HTML (robust) then parses product cards.
    This function raises requests.exceptions.RequestException when the upstream fetch fails.
    """
    # fetch HTML with retries; exceptions propagate
    html = fetch_search_html(query, attempts=int(os.getenv("SCRAPER_FETCH_ATTEMPTS", "4")),
                             connect_timeout=int(os.getenv("SCRAPER_CONNECT_TIMEOUT", DEFAULT_CONNECT_TIMEOUT)),
                             read_timeout=int(os.getenv("SCRAPER_READ_TIMEOUT", DEFAULT_READ_TIMEOUT)))
    soup = BeautifulSoup(html, "html.parser")

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
                print(f"[scraper] found {len(found)} candidates with selector: {sel}")
            break

    # anchor fallback
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
            print(f"[scraper] fallback anchors found: {len(candidates)}")

    results: List[Dict] = []
    title_selectors = ["div._4rR01T", "a.s1Q9rs", "a.IRpwTa", "div._2WkVRV", "span.B_NuCI", "div._3wU53n"]
    price_selectors = ["div._30jeq3", "div._1vC4OE", "div._25b18c", "span._2-ut7f"]

    for idx, card in enumerate(candidates):
        if len(results) >= max_results:
            break
        try:
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

            # TITLE extraction with clean fallback
            title = None
            for ts in title_selectors:
                t = card.select_one(ts)
                if t and t.get_text(strip=True):
                    title = t.get_text(strip=True)
                    break
            if not title and a_tag:
                title = (a_tag.get("title") or a_tag.get_text(strip=True)) or None

            if not title:
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

            # RATING
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

            if not item["title"] and not item["link"]:
                if verbose:
                    print(f"[scraper] skipping candidate #{idx}: no title and no link")
                continue

            results.append(item)

            if verbose:
                found = [k for k, v in item.items() if v is not None]
                missing = [k for k, v in item.items() if v is None]
                print(f"[scraper] candidate #{idx} -> found: {found} | missing: {missing}")

        except Exception as e:
            if verbose:
                print(f"[scraper] error processing candidate #{idx}: {e}")
                traceback.print_exc()
            continue

    if verbose:
        print(f"[scraper] scraped {len(results)} items for query={query}")

    return results
