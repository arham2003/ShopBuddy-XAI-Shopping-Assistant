# ============================================================
# amazon_scraper.py - Fast Amazon.ae Scraper v3.0
# Uses curl_cffi + BeautifulSoup (TLS fingerprint impersonation)
# Bypasses Amazon CAPTCHA via browser TLS impersonation
# ============================================================

from curl_cffi.requests import AsyncSession
import asyncio
import json
import re
import random
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse, urlencode, quote_plus


# ===================== SAFE TYPE HELPERS =====================

def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, list):
        return " | ".join(str(v) for v in value if v)
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        if isinstance(value, str):
            cleaned = re.sub(r'[^\d.]', '', value)
            return float(cleaned) if cleaned else default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        if isinstance(value, str):
            cleaned = re.sub(r'[^\d]', '', value)
            return int(cleaned) if cleaned else default
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_list(value: Any, default: list = None) -> list:
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value.strip() else default
    return [value]


# ===================== ASIN EXTRACTOR =====================

def extract_asin(url: str) -> str:
    """
    Extract ASIN from ANY Amazon URL format.

    Handles:
    - https://www.amazon.ae/Product-Name/dp/B0CQK97MRG/ref=sr_1_2?...
    - https://www.amazon.com/dp/B0CQK97MRG
    - https://www.amazon.ae/gp/product/B0CQK97MRG
    - https://amazon.ae/dp/B0CQK97MRG/
    - Just the ASIN: B0CQK97MRG
    """
    if not url:
        return ""

    # If it's already just an ASIN (10 alphanumeric characters starting with B0)
    url = url.strip()
    if re.match(r'^[A-Z0-9]{10}$', url):
        return url

    # Pattern 1: /dp/ASIN
    match = re.search(r'/dp/([A-Z0-9]{10})', url, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Pattern 2: /gp/product/ASIN
    match = re.search(r'/gp/product/([A-Z0-9]{10})', url, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Pattern 3: /gp/aw/d/ASIN (mobile)
    match = re.search(r'/gp/aw/d/([A-Z0-9]{10})', url, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    # Pattern 4: /ASIN/ anywhere in URL
    match = re.search(r'/([A-Z0-9]{10})(?:/|\?|$)', url, re.IGNORECASE)
    if match:
        candidate = match.group(1).upper()
        # Verify it looks like an ASIN (starts with B0 or is all alphanumeric)
        if candidate.startswith('B0') or re.match(r'^[A-Z0-9]{10}$', candidate):
            return candidate

    return ""


def clean_amazon_url(url: str, domain: str = "amazon.ae") -> str:
    """Clean Amazon URL - strip tracking params, keep only /dp/ASIN"""
    asin = extract_asin(url)
    if asin:
        return f"https://www.{domain}/dp/{asin}"
    return url


def build_amazon_product_url(asin: str, domain: str = "amazon.ae") -> str:
    """Build a clean Amazon product URL from an ASIN."""
    return f"https://www.{domain}/dp/{asin}"


def build_amazon_search_url(query: str, page: int = 1, domain: str = "amazon.ae") -> str:
    """Build an Amazon search URL."""
    return f"https://www.{domain}/s?k={quote_plus(query)}&page={page}"


# ===================== URL DOMAIN DETECTOR =====================

AMAZON_DOMAINS = {
    "amazon.ae": {"currency": "AED", "name": "Amazon UAE"},
    "amazon.com": {"currency": "USD", "name": "Amazon US"},
    "amazon.co.uk": {"currency": "GBP", "name": "Amazon UK"},
    "amazon.sa": {"currency": "SAR", "name": "Amazon Saudi"},
    "amazon.in": {"currency": "INR", "name": "Amazon India"},
    "amazon.de": {"currency": "EUR", "name": "Amazon Germany"},
    "amazon.ca": {"currency": "CAD", "name": "Amazon Canada"},
}


def detect_domain(url: str) -> str:
    """Detect Amazon domain from URL."""
    for domain in AMAZON_DOMAINS:
        if domain in url:
            return domain
    return "amazon.ae"  # Default


# ===================== PYDANTIC SCHEMAS =====================

class CustomerReview(BaseModel):
    """A single customer review from Amazon."""
    reviewer_name: str = ""
    rating: float = 0.0
    title: str = ""
    text: str = ""
    date: str = ""
    verified_purchase: bool = False

    @field_validator('reviewer_name', 'title', 'text', 'date', mode='before')
    @classmethod
    def ensure_string(cls, v):
        return safe_str(v)

    @field_validator('rating', mode='before')
    @classmethod
    def ensure_float(cls, v):
        return safe_float(v)


class ProductDescription(BaseModel):
    short_description: str = ""
    long_description: str = ""
    highlights: list[str] = []
    specifications: dict = {}
    whats_in_the_box: str = ""
    raw_html_description: str = ""

    @field_validator('short_description', 'long_description', 'whats_in_the_box', 'raw_html_description', mode='before')
    @classmethod
    def ensure_string(cls, v):
        return safe_str(v)

    @field_validator('highlights', mode='before')
    @classmethod
    def ensure_list(cls, v):
        return safe_list(v)

    @field_validator('specifications', mode='before')
    @classmethod
    def ensure_dict(cls, v):
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class AmazonProduct(BaseModel):
    product_id: str = ""        # ASIN
    asin: str = ""              # Explicit ASIN field
    name: str = ""
    price: float = 0.0
    original_price: float = 0.0
    currency: str = "AED"
    discount: str = ""
    discount_percentage: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    seller_name: str = ""
    brand: str = ""
    category: str = ""
    image_url: str = ""
    product_url: str = ""
    availability: str = ""
    is_prime: bool = False
    is_best_seller: bool = False
    is_amazon_choice: bool = False
    sales_volume: str = ""
    top_reviews: list[CustomerReview] = []
    platform: str = "amazon"
    domain: str = "amazon.ae"
    description: ProductDescription = ProductDescription()
    source_method: str = "amazon_curl_cffi_bs4"
    scraped_at: str = ""

    @field_validator(
        'product_id', 'asin', 'name', 'currency', 'discount', 'seller_name',
        'brand', 'category', 'image_url', 'product_url', 'availability',
        'sales_volume', 'platform', 'domain', 'source_method', 'scraped_at',
        mode='before'
    )
    @classmethod
    def ensure_string(cls, v):
        return safe_str(v)

    @field_validator('price', 'original_price', 'discount_percentage', 'rating', mode='before')
    @classmethod
    def ensure_float(cls, v):
        return safe_float(v)

    @field_validator('review_count', mode='before')
    @classmethod
    def ensure_int(cls, v):
        return safe_int(v)


class AmazonSearchResult(BaseModel):
    query: str
    total_results: int = 0
    products: list[AmazonProduct] = []
    page: int = 1
    domain: str = "amazon.ae"


# ===================== BROWSER IMPERSONATION =====================
# curl_cffi impersonates real browser TLS fingerprints to bypass detection.
# We rotate between different browser versions to avoid pattern detection.

BROWSER_IMPERSONATIONS = [
    "chrome120",
    "chrome119",
    "chrome116",
    "chrome110",
    "chrome107",
    "chrome104",
    "chrome101",
    "chrome100",
    "chrome99",
]


def get_random_impersonation() -> str:
    """Get a random browser impersonation string for curl_cffi."""
    return random.choice(BROWSER_IMPERSONATIONS)


def get_headers(domain: str = "amazon.ae") -> dict:
    """Get realistic browser headers. curl_cffi handles User-Agent and TLS."""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }


# ===================== JSON FILE SAVER =====================

OUTPUT_DIR = Path("scraped_data")


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_products_to_json(
    products: list[AmazonProduct],
    filename: Optional[str] = None,
    query: str = "",
) -> str:
    ensure_output_dir()

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:50]
        filename = f"amazon_{safe_query}_{timestamp}.json"

    filepath = OUTPUT_DIR / filename

    data = {
        "metadata": {
            "query": query,
            "total_products": len(products),
            "scraped_at": datetime.now().isoformat(),
            "platform": "amazon",
            "scraper_version": "3.0",
        },
        "products": [product.model_dump() for product in products],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\U0001f4be Saved {len(products)} products to {filepath}")
    return str(filepath)


def save_descriptions_to_json(
    products: list[AmazonProduct],
    filename: Optional[str] = None,
    query: str = "",
) -> str:
    ensure_output_dir()

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:50]
        filename = f"amazon_descriptions_{safe_query}_{timestamp}.json"

    filepath = OUTPUT_DIR / filename

    descriptions_data = {
        "metadata": {
            "query": query,
            "total_products": len(products),
            "scraped_at": datetime.now().isoformat(),
            "note": "Descriptions + reviews extracted for XAI Shopping Assistant analysis",
        },
        "product_descriptions": [
            {
                "product_id": p.asin,
                "asin": p.asin,
                "name": p.name,
                "price": p.price,
                "currency": p.currency,
                "is_prime": p.is_prime,
                "is_best_seller": p.is_best_seller,
                "is_amazon_choice": p.is_amazon_choice,
                "product_url": p.product_url,
                "description": p.description.model_dump(),
                "top_reviews": [r.model_dump() for r in p.top_reviews],
            }
            for p in products
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(descriptions_data, f, indent=2, ensure_ascii=False)

    print(f"\U0001f4dd Saved {len(products)} descriptions to {filepath}")
    return str(filepath)


# ===================== HTML PARSERS =====================

def _clean_html_to_text(html_str: str) -> str:
    if not html_str:
        return ""
    html_str = safe_str(html_str)
    soup = BeautifulSoup(html_str, "html.parser")
    for element in soup(["script", "style"]):
        element.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _parse_amazon_price(text: str) -> float:
    """Parse Amazon price from text like 'AED 49.99' or '$29.99' or '2,499.00'"""
    if not text:
        return 0.0
    cleaned = re.sub(r'[^\d.,]', '', text)
    # Handle comma as thousands separator
    cleaned = cleaned.replace(',', '')
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


# ===================== SEARCH SCRAPER =====================

async def search_amazon(
    query: str,
    page: int = 1,
    max_pages: int = 1,
    domain: str = "amazon.ae",
    save_json: bool = True,
) -> AmazonSearchResult:
    """
    Search Amazon and parse product listings from search results HTML.

    Amazon search URL format: https://www.amazon.ae/s?k=gaming+mouse&page=1
    Products are in div elements with data-asin attribute.
    ~16-48 products per page.
    """

    all_products = []
    total_results = 0

    impersonation = get_random_impersonation()
    async with AsyncSession(
        timeout=30,
        impersonate=impersonation,
    ) as client:
        for p in range(page, page + max_pages):
            headers = get_headers(domain)
            url = build_amazon_search_url(query, page=p, domain=domain)

            try:
                # Add a random delay between pages to seem human
                if p > page:
                    await asyncio.sleep(random.uniform(2.0, 5.0))

                response = await client.get(url, headers=headers, allow_redirects=True)

                # CAPTCHA retry with browser impersonation rotation
                max_retries = 3
                for retry in range(max_retries):
                    is_captcha = False

                    if response.status_code == 503:
                        is_captcha = True
                    elif response.status_code == 200:
                        html_check = response.text[:2000].lower()
                        if "captcha" in html_check or "robot" in html_check:
                            is_captcha = True

                    if not is_captcha:
                        break

                    # Rotate impersonation and retry with increasing delay
                    wait_time = (retry + 1) * random.uniform(3.0, 6.0)
                    new_imp = get_random_impersonation()
                    print(f"   \u26a0\ufe0f  CAPTCHA/block detected on page {p} (attempt {retry + 1}/{max_retries}). "
                          f"Switching to {new_imp}, waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)

                    # Create a new session with different impersonation
                    async with AsyncSession(
                        timeout=30,
                        impersonate=new_imp,
                    ) as retry_client:
                        response = await retry_client.get(url, headers=get_headers(domain), allow_redirects=True)

                if response.status_code != 200:
                    print(f"[Amazon Search] Page {p} returned status {response.status_code}")
                    continue

                html = response.text

                # Final CAPTCHA check after all retries
                if "captcha" in html[:3000].lower() or "robot" in html[:3000].lower():
                    print(f"   \u26a0\ufe0f  CAPTCHA persists on page {p} after {max_retries} retries. Skipping.")
                    break

                soup = BeautifulSoup(html, "html.parser")

                # Extract total results count (first page only)
                if p == page:
                    results_bar = soup.select_one("span.s-desktop-toolbar span.sg-col-inner span")
                    if not results_bar:
                        results_bar = soup.select_one("div.s-breadcrumb span:last-child")
                    if results_bar:
                        count_match = re.search(r'([\d,]+)\s+results', results_bar.get_text())
                        if count_match:
                            total_results = safe_int(count_match.group(1))

                # Find all product cards with data-asin
                product_cards = soup.select('div[data-asin]')

                if not product_cards:
                    # Fallback selector
                    product_cards = soup.select('div.s-result-item[data-asin]')

                products_found = 0
                for card in product_cards:
                    asin = card.get("data-asin", "").strip()
                    if not asin or len(asin) != 10:
                        continue  # Skip non-product elements (ads, banners, etc.)

                    try:
                        product = _parse_search_card(card, asin, domain)
                        if product and product.name:  # Only add if we got a name
                            all_products.append(product)
                            products_found += 1
                    except Exception as e:
                        print(f"   \u26a0\ufe0f  Skipped ASIN {asin} (parse error: {e})")
                        continue

                print(f"   \U0001f4c4 Page {p}: found {products_found} products")

                if products_found == 0:
                    break  # No more results

            except Exception as e:
                print(f"[Amazon Search] Page {p} failed: {e}")
                continue

    result = AmazonSearchResult(
        query=query,
        total_results=total_results,
        products=all_products,
        page=page,
        domain=domain,
    )

    if save_json and all_products:
        save_products_to_json(all_products, query=query)

    return result


def _parse_search_card(card, asin: str, domain: str) -> Optional[AmazonProduct]:
    """Parse a single product card from Amazon search results."""

    currency_symbol = AMAZON_DOMAINS.get(domain, {}).get("currency", "AED")

    # ---- Product Name ----
    name = ""
    # Try multiple selectors for product title
    title_selectors = [
        "h2 a span",
        "h2 span",
        "span.a-text-normal",
        "a.a-link-normal span.a-text-normal",
    ]
    for sel in title_selectors:
        title_el = card.select_one(sel)
        if title_el and title_el.get_text(strip=True):
            name = title_el.get_text(strip=True)
            break

    if not name:
        return None  # Skip cards without a product name

    # ---- Price ----
    price = 0.0
    original_price = 0.0

    # Current price
    price_selectors = [
        "span.a-price span.a-offscreen",
        "span.a-price:not([data-a-strike]) span.a-offscreen",
        "span.a-color-base",
    ]
    for sel in price_selectors:
        price_el = card.select_one(sel)
        if price_el:
            price = _parse_amazon_price(price_el.get_text())
            if price > 0:
                break

    # Original/struck price
    original_price_el = card.select_one("span.a-price[data-a-strike] span.a-offscreen")
    if original_price_el:
        original_price = _parse_amazon_price(original_price_el.get_text())
    if original_price == 0:
        original_price = price

    # ---- Rating ----
    rating = 0.0
    rating_el = card.select_one("span.a-icon-alt")
    if rating_el:
        rating_match = re.search(r'([\d.]+)\s+out\s+of', rating_el.get_text())
        if rating_match:
            rating = safe_float(rating_match.group(1))

    # ---- Review Count ----
    review_count = 0
    review_selectors = [
        "span.a-size-base.s-underline-text",
        "a[href*='#customerReviews'] span",
        "span.a-size-base",
    ]
    for sel in review_selectors:
        review_el = card.select_one(sel)
        if review_el:
            review_text = review_el.get_text(strip=True).replace(',', '')
            review_match = re.search(r'([\d]+)', review_text)
            if review_match:
                count = safe_int(review_match.group(1))
                if count > 0:
                    review_count = count
                    break

    # ---- Image ----
    image_url = ""
    img_el = card.select_one("img.s-image")
    if img_el:
        image_url = img_el.get("src", "")

    # ---- Product URL ----
    product_url = ""
    link_el = card.select_one("a.a-link-normal.s-no-outline")
    if not link_el:
        link_el = card.select_one("h2 a")
    if not link_el:
        link_el = card.select_one("a[href*='/dp/']")
    if link_el:
        href = link_el.get("href", "")
        if href:
            if href.startswith("/"):
                product_url = f"https://www.{domain}{href}"
            else:
                product_url = href
    # Always build a clean URL from ASIN
    clean_url = build_amazon_product_url(asin, domain)

    # ---- Badges ----
    is_prime = bool(card.select_one("i.a-icon-prime"))
    is_best_seller = bool(card.select_one("span.a-badge-text"))
    is_amazon_choice = "Amazon's Choice" in card.get_text()

    # ---- Sales Volume ----
    sales_volume = ""
    sales_el = card.select_one("span.a-size-base.a-color-secondary")
    if sales_el:
        text = sales_el.get_text(strip=True)
        if "bought" in text.lower():
            sales_volume = text

    # ---- Discount ----
    discount_pct = 0.0
    if original_price > 0 and price > 0 and price < original_price:
        discount_pct = round((1 - price / original_price) * 100, 1)

    return AmazonProduct(
        product_id=asin,
        asin=asin,
        name=name,
        price=price,
        original_price=original_price,
        currency=currency_symbol,
        discount=f"-{discount_pct}%" if discount_pct > 0 else "",
        discount_percentage=discount_pct,
        rating=rating,
        review_count=review_count,
        image_url=image_url,
        product_url=clean_url,
        is_prime=is_prime,
        is_best_seller=is_best_seller,
        is_amazon_choice=is_amazon_choice,
        sales_volume=sales_volume,
        platform="amazon",
        domain=domain,
        description=ProductDescription(
            short_description=name,  # Search results don't have descriptions
        ),
        source_method="amazon_search_bs4",
        scraped_at=datetime.now().isoformat(),
    )



# ===================== PRODUCT DETAIL SCRAPER =====================

async def get_product_details(
    product_url_or_asin: str,
    domain: str = "amazon.ae",
    session: Optional[AsyncSession] = None,
) -> Optional[AmazonProduct]:
    """
    Scrape product details + top reviews from Amazon.
    Fetches product page for details, then reviews page for top reviews.
    If a shared session is provided, reuses it (faster).
    """
    asin = extract_asin(product_url_or_asin)
    if not asin:
        print(f"[Amazon Detail] Could not extract ASIN from: {product_url_or_asin}")
        return None

    if "amazon." in product_url_or_asin:
        domain = detect_domain(product_url_or_asin)

    clean_url = build_amazon_product_url(asin, domain)
    currency_symbol = AMAZON_DOMAINS.get(domain, {}).get("currency", "AED")

    owns_session = session is None
    if owns_session:
        session = AsyncSession(timeout=30, impersonate=get_random_impersonation())

    try:
        headers = get_headers(domain)
        response = await session.get(clean_url, headers=headers, allow_redirects=True)

        # CAPTCHA retry
        if response.status_code == 503 or (
            response.status_code == 200 and "captcha" in response.text[:2000].lower()
        ):
            wait_time = random.uniform(1.5, 3.0)
            print(f"   \u26a0\ufe0f  CAPTCHA for {asin}, retrying in {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)
            response = await session.get(clean_url, headers=get_headers(domain), allow_redirects=True)

        if response.status_code != 200:
            print(f"[Amazon Detail] {asin} returned status {response.status_code}")
            return None

        html = response.text
        if "captcha" in html[:3000].lower():
            print(f"   \u26a0\ufe0f  CAPTCHA persists for {asin}")
            return None

        product = _parse_product_page(html, asin, clean_url, domain, currency_symbol)

        return product

    except Exception as e:
        print(f"[Amazon Detail] Error fetching {asin}: {e}")
        return None
    finally:
        if owns_session:
            await session.close()


def _parse_product_page(
    html: str,
    asin: str,
    url: str,
    domain: str,
    currency: str,
) -> AmazonProduct:
    """Parse a full Amazon product page HTML."""

    soup = BeautifulSoup(html, "html.parser")

    # ==================== TITLE ====================
    name = ""
    title_el = soup.select_one("#productTitle")
    if title_el:
        name = title_el.get_text(strip=True)

    # ==================== PRICE ====================
    price = 0.0
    original_price = 0.0

    # Try multiple price selectors (Amazon changes these frequently)
    price_selectors = [
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "span.a-price span.a-offscreen",
        "#corePrice_feature_div span.a-offscreen",
        "#apex_offerDisplay_desktop span.a-offscreen",
        "div#corePrice_feature_div span.a-price span.a-offscreen",
        "#tp_price_block_total_price_ww span.a-offscreen",
        "span.priceToPay span.a-offscreen",
    ]
    for sel in price_selectors:
        price_el = soup.select_one(sel)
        if price_el:
            parsed = _parse_amazon_price(price_el.get_text())
            if parsed > 0:
                price = parsed
                break

    # Original price (struck through)
    orig_selectors = [
        "span.a-price[data-a-strike] span.a-offscreen",
        "#priceblock_ourprice_row span.priceBlockStrikePriceString",
        "span.basisPrice span.a-offscreen",
    ]
    for sel in orig_selectors:
        orig_el = soup.select_one(sel)
        if orig_el:
            parsed = _parse_amazon_price(orig_el.get_text())
            if parsed > 0:
                original_price = parsed
                break
    if original_price == 0:
        original_price = price

    # ==================== RATING ====================
    rating = 0.0
    rating_el = soup.select_one("#acrPopover span.a-icon-alt")
    if not rating_el:
        rating_el = soup.select_one("span.a-icon-alt")
    if rating_el:
        rating_match = re.search(r'([\d.]+)\s+out\s+of', rating_el.get_text())
        if rating_match:
            rating = safe_float(rating_match.group(1))

    # ==================== REVIEW COUNT ====================
    review_count = 0
    review_el = soup.select_one("#acrCustomerReviewText")
    if review_el:
        review_count = safe_int(review_el.get_text())

    # ==================== BRAND ====================
    brand = ""
    brand_el = soup.select_one("#bylineInfo")
    if brand_el:
        brand_text = brand_el.get_text(strip=True)
        brand = re.sub(r'^(Visit the|Brand:)\s*', '', brand_text).replace(' Store', '').strip()

    # ==================== BULLET POINTS / HIGHLIGHTS ====================
    highlights = []
    about_section = soup.select_one("#feature-bullets")
    if about_section:
        for li in about_section.select("li span.a-list-item"):
            text = li.get_text(strip=True)
            if text and len(text) > 3 and "see more" not in text.lower():
                highlights.append(text)

    # ==================== PRODUCT DESCRIPTION ====================
    long_description = ""
    raw_html_desc = ""

    # Method 1: #productDescription
    desc_el = soup.select_one("#productDescription")
    if desc_el:
        raw_html_desc = str(desc_el)
        long_description = desc_el.get_text(separator="\n", strip=True)

    # Method 2: #aplus content (A+ description)
    if not long_description:
        aplus = soup.select_one("#aplus")
        if not aplus:
            aplus = soup.select_one("#aplusProductDescription")
        if aplus:
            raw_html_desc = str(aplus)
            long_description = aplus.get_text(separator="\n", strip=True)

    # Method 3: Look in bookDescription_feature_div (for books/digital)
    if not long_description:
        book_desc = soup.select_one("#bookDescription_feature_div")
        if book_desc:
            raw_html_desc = str(book_desc)
            long_description = book_desc.get_text(separator="\n", strip=True)

    # Build short description from highlights or long description
    short_description = " | ".join(highlights[:3]) if highlights else ""
    if not short_description and long_description:
        short_description = long_description[:200].strip()
        if len(long_description) > 200:
            short_description += "..."

    # ==================== SPECIFICATIONS ====================
    specs = {}

    # Method 1: Product details table
    detail_table = soup.select_one("#productDetails_techSpec_section_1")
    if detail_table:
        for row in detail_table.select("tr"):
            header = row.select_one("th")
            value = row.select_one("td")
            if header and value:
                specs[header.get_text(strip=True)] = value.get_text(strip=True)

    # Method 2: Technical details table
    if not specs:
        tech_table = soup.select_one("#productDetails_detailBullets_sections1")
        if tech_table:
            for row in tech_table.select("tr"):
                header = row.select_one("th")
                value = row.select_one("td")
                if header and value:
                    specs[header.get_text(strip=True)] = value.get_text(strip=True)

    # Method 3: Detail bullets (key-value list)
    if not specs:
        detail_bullets = soup.select_one("#detailBullets_feature_div")
        if detail_bullets:
            for li in detail_bullets.select("li"):
                spans = li.select("span.a-list-item span")
                if len(spans) >= 2:
                    key = spans[0].get_text(strip=True).rstrip(':').rstrip('\u200e').strip()
                    val = spans[1].get_text(strip=True)
                    if key and val:
                        specs[key] = val

    # Method 4: Product overview table
    if not specs:
        overview = soup.select_one("#productOverview_feature_div table")
        if overview:
            for row in overview.select("tr"):
                cells = row.select("td")
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    if key and val:
                        specs[key] = val

    # ==================== IMAGES ====================
    image_url = ""
    # Method 1: Main image
    img_el = soup.select_one("#landingImage")
    if img_el:
        image_url = img_el.get("src", "") or img_el.get("data-old-hires", "")

    # Method 2: From embedded JS (hiRes images)
    if not image_url:
        hi_res_match = re.search(r'"hiRes"\s*:\s*"(https://[^"]+)"', html)
        if hi_res_match:
            image_url = hi_res_match.group(1)

    # Method 3: Fallback to any product image
    if not image_url:
        img_el = soup.select_one("#imgTagWrapperId img")
        if img_el:
            image_url = img_el.get("src", "")

    # ==================== SELLER ====================
    seller_name = ""
    seller_el = soup.select_one("#sellerProfileTriggerId")
    if not seller_el:
        seller_el = soup.select_one("#merchant-info a")
    if not seller_el:
        # Check "Sold by" text
        sold_by = soup.select_one("#tabular-buybox-truncate-0 span.a-truncate-cut")
        if sold_by:
            seller_name = sold_by.get_text(strip=True)
    if seller_el and not seller_name:
        seller_name = seller_el.get_text(strip=True)

    # ==================== AVAILABILITY ====================
    availability = ""
    avail_el = soup.select_one("#availability span")
    if avail_el:
        availability = avail_el.get_text(strip=True)

    # ==================== BADGES ====================
    is_prime = bool(soup.select_one("i.a-icon-prime"))
    is_best_seller = bool(soup.select_one("#zeitgeistBadge_feature_div"))
    is_amazon_choice = bool(soup.select_one("#acBadge_feature_div"))

    # ==================== CATEGORY ====================
    category = ""
    breadcrumb = soup.select_one("#wayfinding-breadcrumbs_feature_div")
    if breadcrumb:
        crumbs = breadcrumb.select("a")
        if crumbs:
            category = " > ".join(c.get_text(strip=True) for c in crumbs)

    # ==================== DISCOUNT ====================
    discount_pct = 0.0
    if original_price > 0 and price > 0 and price < original_price:
        discount_pct = round((1 - price / original_price) * 100, 1)

    # Also check for savings text
    savings_el = soup.select_one("span.savingsPercentage")
    if savings_el:
        savings_text = savings_el.get_text(strip=True)
        savings_match = re.search(r'(\d+)', savings_text)
        if savings_match and discount_pct == 0:
            discount_pct = safe_float(savings_match.group(1))

    # ==================== TOP CUSTOMER REVIEWS ====================
    top_reviews = []
    # Reviews on product page are typically li elements with data-hook='review'
    review_containers = soup.select("li[data-hook='review']")
    if not review_containers:
        review_containers = soup.select("div[data-hook='review']")
    if not review_containers:
        review_containers = soup.select(".review")
    
    for rev in review_containers[:5]:  # Top 5 reviews
        try:
            # Reviewer name
            name_el = rev.select_one(".a-profile-name")
            rev_name = name_el.get_text(strip=True) if name_el else ""

            # Rating
            rev_rating = 0.0
            rating_el = rev.select_one(".review-rating .a-icon-alt")
            if not rating_el:
                rating_el = rev.select_one("i[data-hook='review-star-rating'] span.a-icon-alt")
            if rating_el:
                r_match = re.search(r'([\d.]+)', rating_el.get_text())
                if r_match:
                    rev_rating = safe_float(r_match.group(1))

            # Title
            title_el = rev.select_one("a[data-hook='review-title'] span:last-of-type")
            if not title_el:
                title_el = rev.select_one("a[data-hook='review-title']")
            rev_title = ""
            if title_el:
                rev_title = title_el.get_text(strip=True)
                rev_title = re.sub(r'^\d+\.\d+ out of \d+ stars?\s*', '', rev_title).strip()

            # Review text
            text_el = rev.select_one("span[data-hook='review-body'] .review-text-content")
            if not text_el:
                text_el = rev.select_one("span[data-hook='review-body']")
            rev_text = text_el.get_text(strip=True) if text_el else ""

            # Date
            date_el = rev.select_one("span[data-hook='review-date']")
            rev_date = date_el.get_text(strip=True) if date_el else ""

            # Verified purchase
            verified_el = rev.select_one("span[data-hook='avp-badge']")
            is_verified = bool(verified_el)

            if rev_name or rev_text or rev_title:
                top_reviews.append(CustomerReview(
                    reviewer_name=rev_name,
                    rating=rev_rating,
                    title=rev_title,
                    text=rev_text[:500],
                    date=rev_date,
                    verified_purchase=is_verified,
                ))
        except Exception:
            continue

    return AmazonProduct(
        product_id=asin,
        asin=asin,
        name=name,
        price=price if price > 0 else original_price,
        original_price=original_price if original_price > 0 else price,
        currency=currency,
        discount=f"-{discount_pct}%" if discount_pct > 0 else "",
        discount_percentage=discount_pct,
        rating=rating,
        review_count=review_count,
        seller_name=seller_name,
        brand=brand,
        category=category,
        image_url=image_url,
        product_url=url,
        availability=availability,
        is_prime=is_prime,
        is_best_seller=is_best_seller,
        is_amazon_choice=is_amazon_choice,
        top_reviews=top_reviews,
        platform="amazon",
        domain=domain,
        description=ProductDescription(
            short_description=short_description,
            long_description=long_description,
            highlights=highlights,
            specifications=specs,
            raw_html_description=raw_html_desc,
        ),
        source_method="amazon_product_page_bs4",
        scraped_at=datetime.now().isoformat(),
    )


# ===================== BATCH SCRAPER =====================

async def batch_get_product_details(
    product_urls_or_asins: list[str],
    domain: str = "amazon.ae",
    save_json: bool = True,
    query: str = "batch",
) -> list[AmazonProduct]:
    """
    Fetch multiple product pages with CONCURRENT requests on a shared session.

    - Shared TLS session = Amazon sees one consistent browser
    - Semaphore(5) = like one browser with 5 tabs open
    - ~8-12s for 10 products (vs 37s sequential)
    """
    results = []
    semaphore = asyncio.Semaphore(5)
    lock = asyncio.Lock()
    completed = [0]
    total = len(product_urls_or_asins)

    async with AsyncSession(
        timeout=30,
        impersonate=get_random_impersonation(),
    ) as session:
        async def _fetch(url_or_asin: str):
            async with semaphore:
                # Small stagger to avoid simultaneous requests
                await asyncio.sleep(random.uniform(0.3, 0.8))
                try:
                    result = await get_product_details(
                        url_or_asin, domain=domain, session=session
                    )
                    async with lock:
                        completed[0] += 1
                        idx = completed[0]
                    if isinstance(result, AmazonProduct):
                        results.append(result)
                        print(f"   \u2705 [{idx}/{total}] {result.asin} \u2014 {result.name[:50]}")
                    else:
                        print(f"   \u274c [{idx}/{total}] Failed to fetch {url_or_asin}")
                except Exception as e:
                    async with lock:
                        completed[0] += 1
                        idx = completed[0]
                    print(f"   \u26a0\ufe0f  [{idx}/{total}] Error for {url_or_asin}: {e}")

        tasks = [_fetch(item) for item in product_urls_or_asins]
        await asyncio.gather(*tasks)

    if save_json and results:
        save_products_to_json(results, query=query)
        save_descriptions_to_json(results, query=query)

    return results


# ===================== SEARCH + ENRICH PIPELINE =====================

async def search_and_enrich(
    query: str,
    max_pages: int = 1,
    enrich_top_n: int = 5,
    domain: str = "amazon.ae",
    save_json: bool = True,
) -> AmazonSearchResult:
    """
    The RECOMMENDED pipeline for your XAI shopping assistant:
    1. Search Amazon (get ~20-48 products per page)
    2. Get full details + descriptions + reviews for top N products
    3. Save everything to JSON

    Total time: ~8-15 seconds for 1 page + 10 enriched products
    """

    print(f"\U0001f50d Searching Amazon ({domain}) for '{query}'...")
    search_results = await search_amazon(query, max_pages=max_pages, domain=domain, save_json=False)

    if not search_results.products:
        print("\u274c No products found.")
        return search_results

    print(f"\u2705 Found {len(search_results.products)} products")

    # Enrich top N with full descriptions
    products_to_enrich = search_results.products[:enrich_top_n]
    asins_to_enrich = [p.asin for p in products_to_enrich if p.asin]

    if asins_to_enrich:
        print(f"\U0001f4e6 Enriching top {len(asins_to_enrich)} products with descriptions + reviews...")

        enriched = await batch_get_product_details(
            asins_to_enrich,
            domain=domain,
            save_json=False,
            query=query,
        )

        # Merge enriched data back
        enriched_map = {ep.asin: ep for ep in enriched if ep.asin}

        for i, product in enumerate(search_results.products):
            if product.asin in enriched_map:
                ep = enriched_map[product.asin]
                search_results.products[i].description = ep.description
                search_results.products[i].top_reviews = ep.top_reviews
                search_results.products[i].source_method = "amazon_search+product_page"
                # Upgrade fields from detail page
                if ep.brand and not product.brand:
                    search_results.products[i].brand = ep.brand
                if ep.seller_name:
                    search_results.products[i].seller_name = ep.seller_name
                if ep.availability:
                    search_results.products[i].availability = ep.availability
                if ep.category:
                    search_results.products[i].category = ep.category
                if ep.is_prime:
                    search_results.products[i].is_prime = ep.is_prime
                if ep.price > 0 and product.price == 0:
                    search_results.products[i].price = ep.price
                    search_results.products[i].original_price = ep.original_price

        print(f"\u2705 Enriched {len(enriched)} products with full descriptions + reviews")

    if save_json:
        save_products_to_json(search_results.products, query=query)
        save_descriptions_to_json(search_results.products, query=query)

    return search_results


# ===================== MAIN =====================

async def main():
    print("=" * 70)
    print("\U0001f680 AMAZON SCRAPER v3.0 \u2014 Fast Concurrent + Reviews + TLS Impersonation")
    print("=" * 70)

    # ASK USER FOR INPUT
    query = input("\n\U0001f50e What product do you want to search for on Amazon? \u2192 ").strip()

    if not query:
        print("\u274c No query entered. Exiting.")
        return

    # Domain selection
    print("\n\U0001f30d Select Amazon marketplace:")
    print("   1. amazon.ae (UAE) \u2014 Default")
    print("   2. amazon.com (US)")
    print("   3. amazon.co.uk (UK)")
    print("   4. amazon.sa (Saudi)")
    print("   5. amazon.in (India)")

    domain_choice = input("   Choose (1-5, default: 1) \u2192 ").strip()
    domain_map = {
        "1": "amazon.ae", "2": "amazon.com", "3": "amazon.co.uk",
        "4": "amazon.sa", "5": "amazon.in",
    }
    domain = domain_map.get(domain_choice, "amazon.ae")
    print(f"   \u2192 Using {domain}")

    enrich_count = input("\U0001f4e6 How many top products to get full descriptions for? (default: 5) \u2192 ").strip()
    try:
        enrich_count = int(enrich_count) if enrich_count else 5
    except ValueError:
        enrich_count = 5

    # SEARCH + ENRICH
    import time
    start = time.time()

    results = await search_and_enrich(
        query=query,
        max_pages=1,
        enrich_top_n=enrich_count,
        domain=domain,
        save_json=True,
    )

    elapsed = time.time() - start

    print(f"\n{'=' * 70}")
    print(f"\u23f1\ufe0f  Total time: {elapsed:.2f}s for {len(results.products)} products")
    print(f"   ({elapsed/max(len(results.products),1):.2f}s per product on average)")
    print(f"{'=' * 70}")

    # Show sample products
    if results.products:
        print(f"\n\U0001f4e6 TOP {min(3, len(results.products))} PRODUCTS:\n")
        for i, p in enumerate(results.products[:3], 1):
            print(f"   {'\u2500' * 60}")
            print(f"   #{i}")
            print(f"   ASIN:              {p.asin}")
            print(f"   Name:              {p.name[:80]}{'...' if len(p.name) > 80 else ''}")
            print(f"   Price:             {p.currency} {p.price}")
            print(f"   Original Price:    {p.currency} {p.original_price}")
            print(f"   Discount:          {p.discount_percentage}%")
            print(f"   Rating:            {p.rating} ({p.review_count} reviews)")
            print(f"   Brand:             {p.brand}")
            print(f"   Seller:            {p.seller_name}")
            print(f"   Prime:             {'\u2705' if p.is_prime else '\u274c'}")
            print(f"   URL:               {p.product_url}")
            print(f"\n   \U0001f4dd DESCRIPTION:")
            if p.description.short_description:
                print(f"   Short:             {p.description.short_description[:150]}")
            if p.description.highlights:
                print(f"   Highlights ({len(p.description.highlights)}):")
                for h in p.description.highlights[:5]:
                    print(f"      \u2022 {h[:100]}")
            if p.description.long_description:
                print(f"   Full Desc:         {len(p.description.long_description)} characters")
            if p.description.specifications:
                print(f"   Specifications ({len(p.description.specifications)}):")
                for k, v in list(p.description.specifications.items())[:5]:
                    print(f"      {k}: {v}")
            if p.top_reviews:
                print(f"\n   \U0001f4ac TOP REVIEWS ({len(p.top_reviews)}):")
                for j, rev in enumerate(p.top_reviews[:3], 1):
                    stars = '\u2b50' * int(rev.rating)
                    verified = ' \u2705 Verified' if rev.verified_purchase else ''
                    print(f"      {j}. {stars} {rev.title[:60]}")
                    print(f"         by {rev.reviewer_name}{verified}")
                    if rev.text:
                        print(f"         \"{rev.text[:120]}{'...' if len(rev.text) > 120 else ''}\"")
            print()
    else:
        print("\u274c No products found. Try a different search query.")

    # TEST ASIN EXTRACTION from the provided URL
    print(f"{'=' * 70}")
    print(f"\U0001f52c ASIN EXTRACTION TEST:")
    test_url = "https://www.amazon.ae/Roblox-Digital-Extra-Redeem-Worldwide/dp/B0CQK97MRG/ref=sr_1_2?_encoding=UTF8&content-id=amzn1.sym.fc30acf5"
    extracted = extract_asin(test_url)
    print(f"   URL:  {test_url[:80]}...")
    print(f"   ASIN: {extracted}")
    print(f"   Clean URL: {clean_amazon_url(test_url)}")
    print(f"{'=' * 70}")

    # Show saved files
    print(f"\n\U0001f4c1 SAVED FILES:")
    for f in sorted(Path("scraped_data").glob("*.json")):
        size_kb = f.stat().st_size / 1024
        print(f"   \U0001f4c4 {f.name} ({size_kb:.1f} KB)")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())