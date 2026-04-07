"""
agents/scraper.py — Fetches products from Daraz and Amazon, normalises prices.

Calls both custom scrapers, maps results into the unified product schema,
fetches the live exchange rate, and normalises all prices to the user's
display currency before persisting to Supabase.
"""

from __future__ import annotations

import logging

from database.connection import async_session_maker
from database import crud
from services.currency_service import get_exchange_rate, normalize_product_prices
from tools.daraz_scraper import scrape_daraz_products, map_daraz_product
from tools.amazon_scraper import scrape_amazon_products, map_amazon_product
from tools.review_extractor import extract_reviews_from_product
from graph.state import ShoppingState

logger = logging.getLogger(__name__)


def _build_query_candidates(search_terms: list[str], fallback_query: str = "") -> list[str]:
    """Return ordered unique search terms for sequential scraping fallback."""
    candidates: list[str] = []
    seen: set[str] = set()

    for term in search_terms:
        clean = (term or "").strip()
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(clean)

    if not candidates and fallback_query.strip():
        candidates.append(fallback_query.strip())

    return candidates


async def scraper_node(state: ShoppingState) -> dict:
    """
    LangGraph node: scrapes both sources, normalises prices, saves to Supabase.
    """
    search_terms = state.get("search_terms", [])
    display_currency = state.get("display_currency", "PKR")
    session_id = state.get("session_id", "")
    errors: list[str] = list(state.get("errors", []))

    # Build ordered single-term candidates (try first; fallback only if needed)
    query_candidates = _build_query_candidates(search_terms, state.get("user_query", ""))

    # --- 1. Fetch exchange rate ---
    exchange_rate_usd_to_pkr = 278.0
    exchange_rate_timestamp = ""
    exchange_rate_source = "fallback"

    try:
        async with async_session_maker() as db:
            rate_info = await get_exchange_rate(db)
            exchange_rate_usd_to_pkr = rate_info["usd_to_pkr"]
            exchange_rate_timestamp = rate_info["fetched_at"]
            exchange_rate_source = rate_info["source"]
    except Exception as exc:
        logger.error("Exchange rate fetch failed: %s", exc)
        errors.append(f"Exchange rate unavailable: {exc}")

    # --- 2. Scrape Daraz ---
    raw_daraz: list[dict] = []
    for i, candidate in enumerate(query_candidates):
        try:
            logger.info("Daraz attempt %d/%d with term: '%s'", i + 1, len(query_candidates), candidate)
            raw_daraz = await scrape_daraz_products(candidate, max_pages=1, enrich_top_n=5)
            logger.info("Daraz returned %d raw products for '%s'", len(raw_daraz), candidate)
            if raw_daraz:
                break
        except Exception as exc:
            logger.error("Daraz scrape failed for '%s': %s", candidate, exc)
            if i == len(query_candidates) - 1:
                errors.append(f"Daraz scraper error: {exc}")

    # --- 3. Scrape Amazon ---
    raw_amazon: list[dict] = []
    for i, candidate in enumerate(query_candidates):
        try:
            logger.info("Amazon attempt %d/%d with term: '%s'", i + 1, len(query_candidates), candidate)
            raw_amazon = await scrape_amazon_products(candidate, max_pages=1, enrich_top_n=5)
            logger.info("Amazon returned %d raw products for '%s'", len(raw_amazon), candidate)
            if raw_amazon:
                break
        except Exception as exc:
            logger.error("Amazon scrape failed for '%s': %s", candidate, exc)
            if i == len(query_candidates) - 1:
                errors.append(f"Amazon scraper error: {exc}")

    # If BOTH scrapers failed, bail early
    if not raw_daraz and not raw_amazon:
        errors.append("Both scrapers returned zero products — nothing to process.")
        return {
            "daraz_products": [],
            "amazon_products": [],
            "all_products": [],
            "product_reviews": {},
            "exchange_rate_usd_to_pkr": exchange_rate_usd_to_pkr,
            "exchange_rate_timestamp": exchange_rate_timestamp,
            "exchange_rate_source": exchange_rate_source,
            "current_step": "scraper_done",
            "errors": errors,
        }

    # --- 4. Map to unified format & extract reviews (lightweight) ---
    daraz_unified = [map_daraz_product(p) for p in raw_daraz]
    amazon_unified = [map_amazon_product(p) for p in raw_amazon]
    all_products = daraz_unified + amazon_unified

    # Extract only reviews from raw data (discard bulky raw dicts)
    product_reviews: dict[str, list[dict]] = {}
    for raw in raw_daraz + raw_amazon:
        name = raw.get("name", "")
        if name:
            reviews = extract_reviews_from_product(raw)
            if reviews:
                product_reviews[name.lower()] = reviews

    # --- 5. Normalise prices to display currency ---
    try:
        async with async_session_maker() as db:
            all_products = await normalize_product_prices(
                all_products, display_currency, db
            )
    except Exception as exc:
        logger.error("Price normalisation failed: %s", exc)
        errors.append(f"Price normalisation error: {exc}")

    # --- 6. Persist to Supabase ---
    try:
        async with async_session_maker() as db:
            await crud.save_products(db, session_id, all_products)
            # Update session with exchange rate
            session = await crud.get_search_session(db, session_id)
            if session:
                session.exchange_rate_used = exchange_rate_usd_to_pkr
                await db.commit()
        logger.info("Saved %d products to Supabase for session %s", len(all_products), session_id)
    except Exception as exc:
        logger.error("Failed to save products to Supabase: %s", exc)
        errors.append(f"DB product save failed: {exc}")

    return {
        "daraz_products": daraz_unified,
        "amazon_products": amazon_unified,
        "all_products": all_products,
        "product_reviews": product_reviews,
        "exchange_rate_usd_to_pkr": exchange_rate_usd_to_pkr,
        "exchange_rate_timestamp": exchange_rate_timestamp,
        "exchange_rate_source": exchange_rate_source,
        "current_step": "scraper_done",
        "errors": errors,
    }
