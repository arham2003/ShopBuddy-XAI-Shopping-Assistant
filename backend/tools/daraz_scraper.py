"""
tools/daraz_scraper.py — Wrapper around the existing darazscraper.py.

Imports the battle-tested custom scraper and exposes a clean async interface
that returns plain dicts ready for the unified product pipeline.
"""

from __future__ import annotations

import sys
import os
import logging
import uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Make the root-level scraper importable (it lives one level above /backend)
# ---------------------------------------------------------------------------
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from darazscraper import search_and_enrich as _daraz_search_and_enrich  # noqa: E402


# ---------------------------------------------------------------------------
# Scrape entry point
# ---------------------------------------------------------------------------
async def scrape_daraz_products(
    search_query: str,
    max_pages: int = 1,
    enrich_top_n: int = 5,
) -> list[dict]:
    """
    Scrapes Daraz.pk using the custom AJAX scraper.
    Returns a list of raw product dicts (DarazProduct.model_dump()).
    NO external API keys needed.
    """
    try:
        result = await _daraz_search_and_enrich(
            query=search_query,
            max_pages=max_pages,
            enrich_top_n=enrich_top_n,
            save_json=False,
        )
        products = [p.model_dump() for p in result.products]
        logger.info("[Daraz] Scraped %d products for '%s'", len(products), search_query)
        return products
    except Exception as e:
        logger.error("[Daraz] Scrape failed for '%s': %s", search_query, e)
        return []


# ---------------------------------------------------------------------------
# Mapping to unified product format
# ---------------------------------------------------------------------------
def map_daraz_product(item: dict) -> dict:
    """
    Convert a raw DarazProduct dict into the unified product schema
    expected by the rest of the pipeline.
    """
    return {
        "id": str(uuid.uuid4()),
        "source": "daraz",
        "name": item.get("name", "Unknown Product"),
        "price_original": float(item.get("price", 0)),
        "currency_original": "PKR",
        "price_display": float(item.get("price", 0)),  # will be overwritten by normalizer
        "currency_display": "PKR",                       # will be overwritten by normalizer
        "rating": float(item.get("rating", 0)),
        "review_count": int(item.get("review_count", 0)),
        "product_url": item.get("product_url", ""),
        "image_url": item.get("image_url", ""),
        "discount_percentage": float(item.get("discount_percentage", 0) or 0),
        "brand": item.get("brand") or "Unknown",
        "filter_status": "included",
    }
