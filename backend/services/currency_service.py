"""
services/currency_service.py — ExchangeRate-API integration with 2-tier cache.

Cache tiers:
  Tier 1: In-memory Python dict (fastest, lost on restart)
  Tier 2: Supabase exchange_rate_cache table (survives restarts)
  Tier 3: Hardcoded fallback (if API AND DB both fail)

Refresh policy: at most ONE API call per hour → max 24/day, well under
the 1,500/month free-tier limit.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_cached_exchange_rate, save_exchange_rate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (read once from env via config.py at import time)
# ---------------------------------------------------------------------------
# Deferred import to avoid circular dependency when config loads Settings
_settings = None


def _get_settings():
    global _settings
    if _settings is None:
        from config import settings
        _settings = settings
    return _settings


# ---------------------------------------------------------------------------
# Tier 1: In-memory cache
# ---------------------------------------------------------------------------
_cache: dict = {}
_fetch_lock = asyncio.Lock()  # Prevents duplicate concurrent API calls


def _is_memory_fresh(max_age_hours: int | None = None) -> bool:
    """Check if the in-memory rate is younger than max_age_hours."""
    if "fetched_at" not in _cache:
        return False
    age = max_age_hours or _get_settings().EXCHANGE_RATE_CACHE_HOURS
    return (datetime.now(timezone.utc) - _cache["fetched_at"]) < timedelta(hours=age)


# ---------------------------------------------------------------------------
# Core: get_exchange_rate — the single entry point
# ---------------------------------------------------------------------------
async def get_exchange_rate(db: AsyncSession) -> dict:
    """
    Returns the current USD↔PKR exchange rate, pulling from the fastest
    available tier.

    Response shape:
        {
            "usd_to_pkr": 277.87,
            "pkr_to_usd": 0.003599,
            "fetched_at": "2026-03-28T10:00:00+00:00",
            "source": "exchangerate-api"   # or "database-cache" or "fallback"
        }
    """
    s = _get_settings()

    # --- Tier 1: Memory ---
    if _is_memory_fresh():
        return _build_response(_cache["usd_to_pkr"], _cache["fetched_at"], _cache["source"])

    # Acquire lock so only one coroutine hits Tier 2 / Tier 3 at a time
    async with _fetch_lock:
        # Double-check after acquiring lock (another coroutine may have refreshed)
        if _is_memory_fresh():
            return _build_response(_cache["usd_to_pkr"], _cache["fetched_at"], _cache["source"])

        # --- Tier 2: Supabase DB cache ---
        try:
            cached = await get_cached_exchange_rate(
                db, base="USD", target="PKR", max_age_hours=s.EXCHANGE_RATE_CACHE_HOURS
            )
            if cached:
                _update_memory(cached.rate, cached.fetched_at, "database-cache")
                logger.info("Exchange rate loaded from Supabase cache: %.2f", cached.rate)
                return _build_response(cached.rate, cached.fetched_at, "database-cache")
        except Exception as exc:
            logger.warning("Supabase cache lookup failed: %s", exc)

        # --- Tier 3a: Live API call ---
        rate = await _fetch_from_api(s.EXCHANGE_RATE_API_KEY)
        if rate is not None:
            now = datetime.now(timezone.utc)
            _update_memory(rate, now, "exchangerate-api")
            # Persist to DB (fire-and-forget style, but we await to keep session valid)
            try:
                await save_exchange_rate(db, "USD", "PKR", rate, "exchangerate-api")
            except Exception as exc:
                logger.warning("Failed to persist rate to Supabase: %s", exc)
            logger.info("Exchange rate fetched from API: %.2f", rate)
            return _build_response(rate, now, "exchangerate-api")

        # --- Tier 3b: Hardcoded fallback ---
        logger.warning(
            "Using FALLBACK exchange rate (%.2f). API and DB both unavailable.",
            s.FALLBACK_USD_TO_PKR,
        )
        now = datetime.now(timezone.utc)
        _update_memory(s.FALLBACK_USD_TO_PKR, now, "fallback")
        return _build_response(s.FALLBACK_USD_TO_PKR, now, "fallback")


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------
async def _fetch_from_api(api_key: str) -> float | None:
    """
    Hit ExchangeRate-API and return the USD→PKR rate, or None on failure.
    """
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("result") == "success":
                return float(data["conversion_rates"]["PKR"])
            logger.error("ExchangeRate-API returned non-success: %s", data.get("result"))
            return None
    except Exception as exc:
        logger.error("ExchangeRate-API request failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _update_memory(rate: float, fetched_at: datetime, source: str) -> None:
    _cache["usd_to_pkr"] = rate
    _cache["fetched_at"] = fetched_at
    _cache["source"] = source


def _build_response(rate: float, fetched_at: datetime, source: str) -> dict:
    return {
        "usd_to_pkr": rate,
        "pkr_to_usd": round(1.0 / rate, 6) if rate else 0.0,
        "fetched_at": fetched_at.isoformat(),
        "source": source,
    }


# ---------------------------------------------------------------------------
# Pure conversion helper (sync — no DB or API needed)
# ---------------------------------------------------------------------------
def convert_price(
    amount: float,
    from_currency: str,
    to_currency: str,
    usd_to_pkr_rate: float,
) -> float:
    """
    Convert a price between PKR, USD, and AED using the given USD→PKR rate.
    Returns the converted amount rounded to 2 decimal places.
    """
    # Normalize empty/missing currency strings
    from_currency = (from_currency or "USD").upper().strip()
    to_currency = (to_currency or "PKR").upper().strip()

    if from_currency == to_currency:
        return round(amount, 2)

    # Normalize to USD first, then convert to target
    if from_currency == "USD":
        usd_val = amount
    elif from_currency == "PKR":
        usd_val = amount / usd_to_pkr_rate
    elif from_currency == "AED":
        usd_val = amount * 0.2723  # 1 AED ≈ 0.2723 USD
    else:
        return round(amount, 2)  # unknown currency, return as-is

    if to_currency == "USD":
        return round(usd_val, 2)
    elif to_currency == "PKR":
        return round(usd_val * usd_to_pkr_rate, 2)
    elif to_currency == "AED":
        return round(usd_val / 0.2723, 2)
    else:
        return round(amount, 2)


# ---------------------------------------------------------------------------
# Batch normalizer
# ---------------------------------------------------------------------------
async def normalize_product_prices(
    products: list[dict],
    target_currency: str,
    db: AsyncSession,
) -> list[dict]:
    """
    Takes a list of product dicts, converts all prices to target_currency,
    and sets price_display + currency_display on each product.
    """
    rate_info = await get_exchange_rate(db)
    usd_to_pkr = rate_info["usd_to_pkr"]

    for product in products:
        product["price_display"] = convert_price(
            amount=product["price_original"],
            from_currency=product["currency_original"],
            to_currency=target_currency,
            usd_to_pkr_rate=usd_to_pkr,
        )
        product["currency_display"] = target_currency

    return products
