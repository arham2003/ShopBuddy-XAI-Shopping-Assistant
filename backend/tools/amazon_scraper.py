"""
tools/amazon_scraper.py — Wrapper around the existing amazonscraper.py.

Imports the custom curl_cffi + BeautifulSoup scraper and exposes a clean
async interface that returns plain dicts for the unified product pipeline.

The existing scraper targets Amazon.com (USD currency). Prices are converted
to the user's display currency by the currency service downstream.
"""

from __future__ import annotations

import sys
import os
import logging
import uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Make the root-level scraper importable
# ---------------------------------------------------------------------------
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from amazonscraper import search_and_enrich as _amazon_search_and_enrich  # noqa: E402


# ---------------------------------------------------------------------------
# Scrape entry point
# ---------------------------------------------------------------------------
async def scrape_amazon_products(
    search_query: str,
    max_pages: int = 1,
    enrich_top_n: int = 5,
    domain: str = "amazon.com",
) -> list[dict]:
    """
    Scrapes Amazon using the custom curl_cffi scraper.
    Returns a list of raw product dicts (AmazonProduct.model_dump()).
    NO external API keys needed — uses TLS fingerprint impersonation.
    """
    try:
        result = await _amazon_search_and_enrich(
            query=search_query,
            max_pages=max_pages,
            enrich_top_n=enrich_top_n,
            domain=domain,
            save_json=False,
        )
        products = [p.model_dump() for p in result.products]
        logger.info("[Amazon] Scraped %d products for '%s'", len(products), search_query)
        return products
    except Exception as e:
        logger.error("[Amazon] Scrape failed for '%s': %s", search_query, e)
        return []


# ---------------------------------------------------------------------------
# Mapping to unified product format
# ---------------------------------------------------------------------------
def map_amazon_product(item: dict) -> dict:
    """
    Convert a raw AmazonProduct dict into the unified product schema.
    Amazon.com prices are in USD; downstream currency_service handles conversion.
    """
    return {
        "id": str(uuid.uuid4()),
        "source": "amazon",
        "name": item.get("name", "Unknown Product"),
        "price_original": float(item.get("price", 0)),
        "currency_original": "USD",                       # Amazon.com always USD
        "price_display": float(item.get("price", 0)),    # overwritten by normalizer
        "currency_display": "USD",                        # overwritten by normalizer
        "rating": float(item.get("rating", 0)),
        "review_count": int(item.get("review_count", 0)),
        "product_url": item.get("product_url", ""),
        "image_url": item.get("image_url", ""),
        "discount_percentage": float(item.get("discount_percentage", 0) or 0),
        "brand": item.get("brand") or "Unknown",
        "filter_status": "included",
    }
