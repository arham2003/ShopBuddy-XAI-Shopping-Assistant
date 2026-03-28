# ============================================================
# daraz_scraper.py - Blazing Fast Daraz.pk Scraper v2.1
# BULLETPROOFED against Daraz's inconsistent API types
# ============================================================

import httpx
import asyncio
import json
import re
import os
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse, urlencode, parse_qs


# ===================== SAFE TYPE HELPERS =====================
# Daraz API returns wildly inconsistent types. These ensure we
# NEVER get a Pydantic validation error again.

def safe_str(value: Any, default: str = "") -> str:
    """Convert ANY value to a string safely."""
    if value is None:
        return default
    if isinstance(value, list):
        return " | ".join(str(v) for v in value if v)
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert ANY value to a float safely."""
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
    """Convert ANY value to an int safely."""
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
    """Convert ANY value to a list safely."""
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value.strip() else default
    return [value]


# ===================== URL CLEANER =====================

def clean_daraz_url(url: str) -> str:
    """
    Clean Daraz product URLs by removing tracking parameters.
    Turns a 500-char URL into a clean 80-char URL.

    Before: https://www.daraz.pk/products/led-tws-enc-hifi-53-i943612144-s4003632461.html?clickTrackInfo=...&spm=...
    After:  https://www.daraz.pk/products/led-tws-enc-hifi-53-i943612144-s4003632461.html
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        # Keep only the scheme + netloc + path (strip all query params)
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return clean
    except Exception:
        return url


# ===================== PYDANTIC SCHEMAS =====================

class ProductDescription(BaseModel):
    """Separate model for rich description data"""
    short_description: str = ""
    long_description: str = ""
    highlights: list[str] = []
    specifications: dict = {}
    whats_in_the_box: str = ""
    raw_html_description: str = ""

    # Bulletproof validators
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


class DarazProduct(BaseModel):
    """Unified product schema for your multi-agent system"""
    product_id: str = ""
    name: str = ""
    price: float = 0.0
    original_price: float = 0.0
    currency: str = "PKR"
    discount: str = ""
    discount_percentage: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    seller_name: str = ""
    seller_rating: Optional[float] = None
    brand: str = ""
    category: str = ""
    image_url: str = ""
    product_url: str = ""
    location: str = ""
    stock_status: str = ""
    items_sold: int = 0
    platform: str = "daraz"
    description: ProductDescription = ProductDescription()
    source_method: str = "daraz_json_api"
    scraped_at: str = ""

    # Bulletproof ALL string fields against int/list/dict returns
    @field_validator(
        'product_id', 'name', 'currency', 'discount', 'seller_name',
        'brand', 'category', 'image_url', 'product_url', 'location',
        'stock_status', 'platform', 'source_method', 'scraped_at',
        mode='before'
    )
    @classmethod
    def ensure_string(cls, v):
        return safe_str(v)

    @field_validator('price', 'original_price', 'discount_percentage', 'rating', mode='before')
    @classmethod
    def ensure_float(cls, v):
        return safe_float(v)

    @field_validator('review_count', 'items_sold', mode='before')
    @classmethod
    def ensure_int(cls, v):
        return safe_int(v)


class DarazSearchResult(BaseModel):
    query: str
    total_results: int = 0
    products: list[DarazProduct] = []
    page: int = 1
    total_pages: int = 0


# ===================== JSON FILE SAVER =====================

OUTPUT_DIR = Path("scraped_data")


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def save_products_to_json(
    products: list[DarazProduct],
    filename: Optional[str] = None,
    query: str = "",
) -> str:
    ensure_output_dir()

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:50]
        filename = f"daraz_{safe_query}_{timestamp}.json"

    filepath = OUTPUT_DIR / filename

    data = {
        "metadata": {
            "query": query,
            "total_products": len(products),
            "scraped_at": datetime.now().isoformat(),
            "platform": "daraz.pk",
            "scraper_version": "2.1",
        },
        "products": [product.model_dump() for product in products],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"💾 Saved {len(products)} products to {filepath}")
    return str(filepath)


def save_descriptions_to_json(
    products: list[DarazProduct],
    filename: Optional[str] = None,
    query: str = "",
) -> str:
    ensure_output_dir()

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:50]
        filename = f"daraz_descriptions_{safe_query}_{timestamp}.json"

    filepath = OUTPUT_DIR / filename

    descriptions_data = {
        "metadata": {
            "query": query,
            "total_products": len(products),
            "scraped_at": datetime.now().isoformat(),
            "note": "Descriptions extracted for XAI Shopping Assistant analysis",
        },
        "product_descriptions": [
            {
                "product_id": p.product_id,
                "name": p.name,
                "price": p.price,
                "product_url": p.product_url,
                "description": p.description.model_dump(),
            }
            for p in products
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(descriptions_data, f, indent=2, ensure_ascii=False)

    print(f"📝 Saved {len(products)} descriptions to {filepath}")
    return str(filepath)


# ===================== HEADERS =====================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.daraz.pk/",
}


# ===================== DESCRIPTION EXTRACTOR =====================

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


def _extract_highlights(data: dict) -> list[str]:
    highlights = []

    try:
        highlights_data = (
            data.get("data", {})
            .get("root", {})
            .get("fields", {})
            .get("product", {})
            .get("highlights", [])
        )
        if isinstance(highlights_data, list):
            highlights = [_clean_html_to_text(h) if "<" in str(h) else str(h) for h in highlights_data if h]
    except:
        pass

    if not highlights:
        try:
            detail = data.get("data", {}).get("root", {}).get("fields", {}).get("productDetail", {})
            highlights_html = detail.get("highlights", "")
            if highlights_html:
                soup = BeautifulSoup(safe_str(highlights_html), "html.parser")
                for li in soup.find_all("li"):
                    text = li.get_text(strip=True)
                    if text:
                        highlights.append(text)
        except:
            pass

    if not highlights:
        for key_path in [["highlights"], ["product", "highlights"], ["desc", "highlights"]]:
            try:
                obj = data
                for key in key_path:
                    obj = obj[key]
                if isinstance(obj, list):
                    highlights = [str(h) for h in obj if h]
                elif isinstance(obj, str):
                    soup = BeautifulSoup(obj, "html.parser")
                    for li in soup.find_all("li"):
                        text = li.get_text(strip=True)
                        if text:
                            highlights.append(text)
                break
            except (KeyError, TypeError):
                continue

    return highlights


def _extract_specifications(data: dict) -> dict:
    specs = {}

    try:
        features = (
            data.get("data", {})
            .get("root", {})
            .get("fields", {})
            .get("product", {})
            .get("props", [])
        )
        if isinstance(features, list):
            for prop in features:
                if isinstance(prop, dict):
                    name = safe_str(prop.get("name", prop.get("label", "")))
                    value = safe_str(prop.get("value", ""))
                    if name and value:
                        specs[name] = value
    except:
        pass

    if not specs:
        try:
            sku_infos = (
                data.get("data", {})
                .get("root", {})
                .get("fields", {})
                .get("skuInfos", {})
            )
            for sku_key, sku_val in sku_infos.items():
                if isinstance(sku_val, dict):
                    for prop in sku_val.get("properties", []):
                        name = safe_str(prop.get("name", ""))
                        value = safe_str(prop.get("value", ""))
                        if name and value:
                            specs[name] = value
        except:
            pass

    if not specs:
        for key_path in [
            ["specifications"],
            ["product", "specifications"],
            ["productOption", "options"],
        ]:
            try:
                obj = data
                for key in key_path:
                    obj = obj[key]
                if isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, dict):
                            name = safe_str(item.get("name", item.get("label", "")))
                            value = safe_str(item.get("value", ""))
                            if name and value:
                                specs[name] = value
                            for feat in item.get("features", []):
                                if isinstance(feat, dict):
                                    specs[safe_str(feat.get("name", ""))] = safe_str(feat.get("value", ""))
                elif isinstance(obj, dict):
                    specs = {safe_str(k): safe_str(v) for k, v in obj.items()}
                break
            except (KeyError, TypeError):
                continue

    return specs


def _extract_full_description(data: dict) -> ProductDescription:
    desc = ProductDescription()

    long_desc_html = ""
    desc_paths = [
        ["data", "root", "fields", "productDetail", "description"],
        ["data", "root", "fields", "product", "desc"],
        ["data", "root", "fields", "product", "description"],
        ["product", "desc"],
        ["product", "description"],
        ["description"],
    ]

    for path in desc_paths:
        try:
            obj = data
            for key in path:
                obj = obj[key]
            obj_str = safe_str(obj)
            if len(obj_str) > 10:
                long_desc_html = obj_str
                break
        except (KeyError, TypeError):
            continue

    desc.raw_html_description = long_desc_html
    desc.long_description = _clean_html_to_text(long_desc_html)

    short_paths = [
        ["data", "root", "fields", "product", "title"],
        ["data", "root", "fields", "product", "shortDescription"],
        ["product", "shortDescription"],
    ]
    for path in short_paths:
        try:
            obj = data
            for key in path:
                obj = obj[key]
            obj_str = safe_str(obj)
            if obj_str:
                desc.short_description = obj_str
                break
        except (KeyError, TypeError):
            continue

    if not desc.short_description and desc.long_description:
        desc.short_description = desc.long_description[:200].strip()
        if len(desc.long_description) > 200:
            desc.short_description += "..."

    desc.highlights = _extract_highlights(data)
    desc.specifications = _extract_specifications(data)

    box_paths = [
        ["data", "root", "fields", "product", "whatsInTheBox"],
        ["data", "root", "fields", "productDetail", "whatsInTheBox"],
        ["product", "whatsInTheBox"],
    ]
    for path in box_paths:
        try:
            obj = data
            for key in path:
                obj = obj[key]
            obj_str = safe_str(obj)
            if obj_str:
                desc.whats_in_the_box = _clean_html_to_text(obj_str) if "<" in obj_str else obj_str
                break
        except (KeyError, TypeError):
            continue

    return desc


# ===================== SEARCH SCRAPER =====================

async def search_daraz(
    query: str,
    page: int = 1,
    max_pages: int = 1,
    save_json: bool = True,
) -> DarazSearchResult:
    all_products = []
    total_results = 0
    total_pages = 0

    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
        for p in range(page, page + max_pages):
            url = "https://www.daraz.pk/catalog/"
            params = {
                "ajax": "true",
                "page": str(p),
                "q": query,
            }

            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                list_items = data.get("mods", {}).get("listItems", [])

                if not list_items:
                    break

                if p == page:
                    tips = data.get("mainInfo", {}).get("totalResults", 0)
                    if tips:
                        total_results = safe_int(tips)
                        total_pages = (total_results + 39) // 40

                for item in list_items:
                    try:
                        product = _parse_search_item(item)
                        all_products.append(product)
                    except Exception as e:
                        # Skip individual product parse failures, don't crash entire search
                        print(f"   ⚠️  Skipped 1 product (parse error: {e})")
                        continue

            except Exception as e:
                print(f"[Daraz Search] Page {p} failed: {e}")
                continue

    result = DarazSearchResult(
        query=query,
        total_results=total_results,
        products=all_products,
        page=page,
        total_pages=total_pages,
    )

    if save_json and all_products:
        save_products_to_json(all_products, query=query)

    return result


def _parse_search_item(item: dict) -> DarazProduct:
    """Parse a single product — ALL fields go through safe_* converters."""

    price = safe_float(item.get("price", "0"))
    original_price = safe_float(item.get("originalPrice", item.get("price", "0")))

    discount_pct = 0.0
    discount_str = safe_str(item.get("discount", ""))
    if discount_str:
        try:
            discount_pct = float(re.sub(r'[^\d.]', '', discount_str.replace('%', '')))
        except:
            pass
    elif original_price > 0 and price < original_price:
        discount_pct = round((1 - price / original_price) * 100, 1)

    # Product URL — clean it!
    item_url = safe_str(item.get("productUrl", item.get("itemUrl", "")))
    if item_url and not item_url.startswith("http"):
        item_url = f"https:{item_url}" if item_url.startswith("//") else f"https://www.daraz.pk{item_url}"
    item_url = clean_daraz_url(item_url)

    # Image URL
    image = safe_str(item.get("image", ""))
    if image and not image.startswith("http"):
        image = f"https:{image}" if image.startswith("//") else image

    # *** DESCRIPTION — handle string, list, int, None, anything ***
    raw_desc = item.get("description", "") or ""
    short_desc = ""
    highlights = []

    if isinstance(raw_desc, list):
        highlights = [safe_str(d).strip() for d in raw_desc if d]
        short_desc = " | ".join(highlights)
    else:
        raw_desc_str = safe_str(raw_desc)
        short_desc = _clean_html_to_text(raw_desc_str) if "<" in raw_desc_str else raw_desc_str

    if not short_desc:
        fallback_desc = item.get("shortDescription", "") or ""
        if isinstance(fallback_desc, list):
            highlights = [safe_str(d).strip() for d in fallback_desc if d]
            short_desc = " | ".join(highlights)
        else:
            short_desc = safe_str(fallback_desc)

    # *** CATEGORY — handle int, list, string, anything ***
    raw_categories = item.get("categories", "")
    if isinstance(raw_categories, list) and raw_categories:
        category = safe_str(raw_categories[0])
    else:
        category = safe_str(raw_categories)

    description = ProductDescription(
        short_description=short_desc,
        long_description="",
        highlights=highlights,
        specifications={},
    )

    return DarazProduct(
        product_id=safe_str(item.get("nid", "")),
        name=safe_str(item.get("name", "")),
        price=price,
        original_price=original_price,
        currency="PKR",
        discount=discount_str,
        discount_percentage=discount_pct,
        rating=safe_float(item.get("ratingScore", "0")),
        review_count=safe_int(item.get("review", "0")),
        seller_name=safe_str(item.get("sellerName", "")),
        brand=safe_str(item.get("brandName", "")),
        category=category,
        image_url=image,
        product_url=item_url,
        location=safe_str(item.get("location", "")),
        stock_status="In Stock",
        items_sold=safe_int(item.get("itemSoldCntShow", "0")),
        platform="daraz",
        description=description,
        source_method="daraz_ajax_search",
        scraped_at=datetime.now().isoformat(),
    )


# ===================== PRODUCT DETAIL SCRAPER =====================

async def get_product_details(product_url: str) -> Optional[DarazProduct]:
    # Clean the URL first
    clean_url = clean_daraz_url(product_url)

    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
        try:
            response = await client.get(clean_url)
            response.raise_for_status()
            html = response.text

            page_data = _extract_page_data(html)
            if page_data:
                return _parse_product_page_data(page_data, clean_url)

            app_data = _extract_app_data(html)
            if app_data:
                return _parse_product_page_data(app_data, clean_url)

            return _parse_html_fallback(html, clean_url)

        except Exception as e:
            print(f"[Daraz Detail] Error fetching {clean_url}: {e}")
            return None


def _extract_page_data(html: str) -> Optional[dict]:
    patterns = [
        r'window\.pageData\s*=\s*(\{.+?\})\s*;?\s*<\/script>',
        r'window\.pageData\s*=\s*(\{.+?\})\s*;\s*\n',
        r'app\.run\((\{.*?"data".*?\})\)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                try:
                    raw = match.group(1)
                    depth = 0
                    for i, c in enumerate(raw):
                        if c == '{':
                            depth += 1
                        elif c == '}':
                            depth -= 1
                            if depth == 0:
                                return json.loads(raw[:i+1])
                except:
                    continue
    return None


def _extract_app_data(html: str) -> Optional[dict]:
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and ("name" in data or "@type" in data):
                return data
        except:
            continue

    next_data_script = soup.find("script", id="__NEXT_DATA__")
    if next_data_script:
        try:
            return json.loads(next_data_script.string)
        except:
            pass

    return None


def _parse_html_fallback(html: str, url: str) -> Optional[DarazProduct]:
    soup = BeautifulSoup(html, "html.parser")

    desc_text = ""
    highlights = []

    desc_box = soup.find("div", class_=re.compile(r"detail-content|product-description|pdp-product-desc"))
    if desc_box:
        desc_text = desc_box.get_text(separator="\n", strip=True)

    highlights_box = soup.find("ul", class_=re.compile(r"detail-highlights|product-highlights"))
    if highlights_box:
        for li in highlights_box.find_all("li"):
            text = li.get_text(strip=True)
            if text:
                highlights.append(text)

    title = ""
    title_el = soup.find("h1") or soup.find("span", class_=re.compile(r"pdp-mod-product-badge-title"))
    if title_el:
        title = title_el.get_text(strip=True)

    if not title and not desc_text:
        return None

    return DarazProduct(
        name=title,
        product_url=url,
        description=ProductDescription(
            short_description=desc_text[:200] + "..." if len(desc_text) > 200 else desc_text,
            long_description=desc_text,
            highlights=highlights,
        ),
        source_method="daraz_html_fallback",
        scraped_at=datetime.now().isoformat(),
    )


def _parse_product_page_data(data: dict, url: str) -> DarazProduct:
    product_data = {}

    if "data" in data:
        root = data["data"].get("root", data["data"])
        if "fields" in root:
            product_data = root["fields"].get("product", root["fields"])
        elif "product" in root:
            product_data = root["product"]
        else:
            product_data = root
    elif "product" in data:
        product_data = data["product"]
    elif "@type" in data and data["@type"] == "Product":
        ld_desc = safe_str(data.get("description", ""))
        return DarazProduct(
            product_id=safe_str(data.get("sku", "")),
            name=safe_str(data.get("name", "")),
            price=safe_float(str(data.get("offers", {}).get("price", 0))),
            original_price=safe_float(str(data.get("offers", {}).get("price", 0))),
            currency="PKR",
            rating=safe_float(data.get("aggregateRating", {}).get("ratingValue", 0)),
            review_count=safe_int(data.get("aggregateRating", {}).get("reviewCount", 0)),
            brand=safe_str(
                data.get("brand", {}).get("name", "")
                if isinstance(data.get("brand"), dict)
                else data.get("brand", "")
            ),
            image_url=safe_str(
                data.get("image", [""])[0]
                if isinstance(data.get("image"), list)
                else data.get("image", "")
            ),
            product_url=url,
            description=ProductDescription(
                short_description=ld_desc[:200] + "..." if len(ld_desc) > 200 else ld_desc,
                long_description=ld_desc,
            ),
            platform="daraz",
            source_method="daraz_ldjson",
            scraped_at=datetime.now().isoformat(),
        )
    else:
        product_data = data

    # FULL DESCRIPTION
    description = _extract_full_description(data)

    name = safe_str(
        product_data.get("title", "")
        or product_data.get("name", "")
        or data.get("name", "")
    )

    if not description.short_description:
        description.short_description = name

    price_field = product_data.get("price", "0")
    if isinstance(price_field, dict):
        price = safe_float(price_field.get("salePrice", {}).get("text", "0") if isinstance(price_field.get("salePrice"), dict) else price_field.get("salePrice", "0"))
        original_price = safe_float(price_field.get("originalPrice", {}).get("text", "0") if isinstance(price_field.get("originalPrice"), dict) else price_field.get("originalPrice", "0"))
    else:
        price = safe_float(price_field)
        original_price = safe_float(product_data.get("originalPrice", price_field))

    rating_info = product_data.get("review", product_data.get("ratings", {}))
    rating = 0.0
    review_count = 0
    if isinstance(rating_info, dict):
        rating = safe_float(rating_info.get("average", rating_info.get("score", 0)))
        review_count = safe_int(rating_info.get("totalCount", rating_info.get("count", 0)))

    seller_info = product_data.get("seller", {})
    seller_name = ""
    if isinstance(seller_info, dict):
        seller_name = safe_str(seller_info.get("name", ""))
    else:
        seller_name = safe_str(seller_info)

    brand = product_data.get("brand", "")
    if isinstance(brand, dict):
        brand = safe_str(brand.get("name", ""))
    else:
        brand = safe_str(brand)

    image_url = ""
    images = product_data.get("images", product_data.get("gallery", []))
    if isinstance(images, list) and images:
        img = images[0]
        image_url = safe_str(img.get("src", img) if isinstance(img, dict) else img)
    elif isinstance(images, str):
        image_url = images
    if image_url and not image_url.startswith("http"):
        image_url = f"https:{image_url}" if image_url.startswith("//") else image_url

    return DarazProduct(
        product_id=safe_str(product_data.get("id", product_data.get("itemId", ""))),
        name=name,
        price=price if price > 0 else original_price,
        original_price=original_price if original_price > 0 else price,
        currency="PKR",
        discount=safe_str(product_data.get("discount", "")),
        discount_percentage=(
            round((1 - price / original_price) * 100, 1)
            if original_price > 0 and price > 0 and price < original_price
            else 0.0
        ),
        rating=rating,
        review_count=review_count,
        seller_name=seller_name,
        brand=brand,
        category=safe_str(product_data.get("category", "")),
        image_url=image_url,
        product_url=url,
        stock_status="In Stock" if product_data.get("stock", True) else "Out of Stock",
        platform="daraz",
        description=description,
        source_method="daraz_page_data",
        scraped_at=datetime.now().isoformat(),
    )


# ===================== BATCH SCRAPER =====================

async def batch_get_product_details(
    product_urls: list[str],
    max_concurrent: int = 5,
    save_json: bool = True,
    query: str = "batch",
) -> list[DarazProduct]:
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def _fetch_with_semaphore(url: str):
        async with semaphore:
            result = await get_product_details(url)
            await asyncio.sleep(0.3)
            return result

    tasks = [_fetch_with_semaphore(url) for url in product_urls]
    fetched = await asyncio.gather(*tasks, return_exceptions=True)

    for item in fetched:
        if isinstance(item, DarazProduct):
            results.append(item)
        elif isinstance(item, Exception):
            print(f"   ⚠️  Batch error: {item}")

    if save_json and results:
        save_products_to_json(results, query=query)
        save_descriptions_to_json(results, query=query)

    return results


# ===================== SEARCH + ENRICH PIPELINE =====================

async def search_and_enrich(
    query: str,
    max_pages: int = 1,
    enrich_top_n: int = 10,
    save_json: bool = True,
) -> DarazSearchResult:
    print(f"🔍 Searching Daraz for '{query}'...")
    search_results = await search_daraz(query, max_pages=max_pages, save_json=False)

    if not search_results.products:
        print("❌ No products found.")
        return search_results

    print(f"✅ Found {len(search_results.products)} products")

    products_to_enrich = search_results.products[:enrich_top_n]
    urls_to_enrich = [p.product_url for p in products_to_enrich if p.product_url]

    if urls_to_enrich:
        print(f"📦 Enriching top {len(urls_to_enrich)} products with full descriptions...")

        enriched = await batch_get_product_details(
            urls_to_enrich,
            max_concurrent=5,
            save_json=False,
            query=query,
        )

        enriched_map = {}
        for ep in enriched:
            if ep.product_url:
                enriched_map[ep.product_url] = ep

        for i, product in enumerate(search_results.products):
            if product.product_url in enriched_map:
                enriched_product = enriched_map[product.product_url]
                search_results.products[i].description = enriched_product.description
                search_results.products[i].source_method = "daraz_ajax_search+page_detail"
                if enriched_product.brand and not product.brand:
                    search_results.products[i].brand = enriched_product.brand
                if enriched_product.seller_name and not product.seller_name:
                    search_results.products[i].seller_name = enriched_product.seller_name

        print(f"✅ Enriched {len(enriched)} products with full descriptions")

    if save_json:
        save_products_to_json(search_results.products, query=query)
        save_descriptions_to_json(search_results.products, query=query)

    return search_results


# ===================== UTILITY =====================

def _parse_price(price_str: str) -> float:
    return safe_float(price_str)


# ===================== MAIN =====================

async def main():
    print("=" * 70)
    print("🚀 DARAZ SCRAPER v2.1 — With Descriptions + JSON Saving")
    print("=" * 70)

    # ASK USER FOR SEARCH QUERY
    query = input("\n🔎 What product do you want to search for? → ").strip()

    if not query:
        print("❌ No query entered. Exiting.")
        return

    enrich_count = input("📦 How many top products to get full descriptions for? (default: 5) → ").strip()
    try:
        enrich_count = int(enrich_count) if enrich_count else 5
    except ValueError:
        enrich_count = 5

    # SEARCH + ENRICH PIPELINE
    import time
    start = time.time()

    results = await search_and_enrich(
        query=query,
        max_pages=1,
        enrich_top_n=enrich_count,
        save_json=True,
    )

    elapsed = time.time() - start

    print(f"\n{'=' * 70}")
    print(f"⏱️  Total time: {elapsed:.2f}s for {len(results.products)} products")
    print(f"   ({elapsed/max(len(results.products),1):.2f}s per product on average)")
    print(f"{'=' * 70}")

    # Show sample products
    if results.products:
        print(f"\n📦 TOP {min(3, len(results.products))} PRODUCTS:\n")
        for i, p in enumerate(results.products[:3], 1):
            print(f"   {'─' * 60}")
            print(f"   #{i}")
            print(f"   Name:              {p.name}")
            print(f"   Price:             Rs. {p.price}")
            print(f"   Original Price:    Rs. {p.original_price}")
            print(f"   Discount:          {p.discount_percentage}%")
            print(f"   Rating:            {p.rating} ({p.review_count} reviews)")
            print(f"   Brand:             {p.brand}")
            print(f"   Seller:            {p.seller_name}")
            print(f"   URL:               {p.product_url}")
            print(f"\n   📝 DESCRIPTION:")
            print(f"   Short:             {p.description.short_description[:150]}")
            if p.description.highlights:
                print(f"   Highlights ({len(p.description.highlights)}):")
                for h in p.description.highlights[:5]:
                    print(f"      • {h}")
            if p.description.long_description:
                print(f"   Full Desc:         {len(p.description.long_description)} characters")
            if p.description.specifications:
                print(f"   Specifications ({len(p.description.specifications)}):")
                for k, v in list(p.description.specifications.items())[:5]:
                    print(f"      {k}: {v}")
            if p.description.whats_in_the_box:
                print(f"   What's in box:     {p.description.whats_in_the_box[:100]}")
            print()
    else:
        print("❌ No products found. Try a different search query.")

    # Show saved files
    print(f"{'=' * 70}")
    print(f"📁 SAVED FILES:")
    for f in sorted(Path("scraped_data").glob("*.json")):
        size_kb = f.stat().st_size / 1024
        print(f"   📄 {f.name} ({size_kb:.1f} KB)")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())