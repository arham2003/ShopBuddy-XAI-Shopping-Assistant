"""
database/crud.py — Async CRUD helpers for Supabase PostgreSQL.

Every function receives an AsyncSession and returns ORM model instances.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SearchSession, Product, ExchangeRateCache


# ---------------------------------------------------------------------------
# SearchSession CRUD
# ---------------------------------------------------------------------------
async def create_search_session(
    db: AsyncSession,
    session_data: dict,
) -> SearchSession:
    """Insert a new search session row and return it."""
    session = SearchSession(
        id=session_data.get("id", uuid.uuid4()),
        query=session_data["query"],
        display_currency=session_data.get("display_currency", "PKR"),
        search_terms=session_data.get("search_terms", []),
        budget_max=session_data.get("budget_max"),
        exchange_rate_used=session_data.get("exchange_rate_used", 0.0),
        funnel_stats=session_data.get("funnel_stats", {}),
        fetch_explanation=session_data.get("fetch_explanation", ""),
        is_demo=session_data.get("is_demo", False),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_search_session(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> Optional[SearchSession]:
    """Fetch a single session by primary key (with eager-loaded products)."""
    result = await db.execute(
        select(SearchSession).where(SearchSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_demo_sessions(db: AsyncSession) -> list[SearchSession]:
    """Return all sessions flagged as demo seeds, newest first."""
    result = await db.execute(
        select(SearchSession)
        .where(SearchSession.is_demo == True)  # noqa: E712
        .order_by(SearchSession.created_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Product CRUD
# ---------------------------------------------------------------------------
async def save_products(
    db: AsyncSession,
    session_id: uuid.UUID,
    products: list[dict],
) -> list[Product]:
    """Bulk-insert a list of product dicts and return ORM instances."""
    orm_products: list[Product] = []
    for p in products:
        product = Product(
            id=p.get("id", uuid.uuid4()),
            session_id=session_id,
            source=p["source"],
            name=p["name"],
            price_original=p["price_original"],
            currency_original=p["currency_original"],
            price_display=p["price_display"],
            currency_display=p["currency_display"],
            rating=p.get("rating", 0.0),
            review_count=p.get("review_count", 0),
            product_url=p.get("product_url", ""),
            image_url=p.get("image_url", ""),
            discount_percentage=p.get("discount_percentage"),
            brand=p.get("brand"),
            value_score=p.get("value_score"),
            recommendation_badge=p.get("recommendation_badge"),
            reasoning_chain=p.get("reasoning_chain"),
            cross_platform_note=p.get("cross_platform_note"),
            filter_status=p.get("filter_status", "included"),
            filter_reason=p.get("filter_reason"),
            filter_name=p.get("filter_name"),
            review_sentiment=p.get("review_sentiment"),
            review_positive_themes=p.get("review_positive_themes"),
            review_negative_themes=p.get("review_negative_themes"),
            review_summary=p.get("review_summary"),
        )
        orm_products.append(product)

    db.add_all(orm_products)
    await db.commit()

    # Refresh all to populate server-side defaults
    for product in orm_products:
        await db.refresh(product)

    return orm_products


async def get_products_by_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    filter_status: Optional[str] = None,
) -> list[Product]:
    """Fetch products for a session, optionally filtered by included/excluded."""
    stmt = select(Product).where(Product.session_id == session_id)
    if filter_status:
        stmt = stmt.where(Product.filter_status == filter_status)
    stmt = stmt.order_by(Product.value_score.desc().nulls_last())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_product_prices(
    db: AsyncSession,
    session_id: uuid.UUID,
    new_currency: str,
    exchange_rate: float,
) -> list[Product]:
    """
    Re-convert all product prices in a session to a new display currency.
    Uses the provided USD↔PKR exchange_rate for conversion.
    Returns the updated product list.
    """
    products = await get_products_by_session(db, session_id)

    for product in products:
        orig = product.price_original
        orig_cur = product.currency_original

        if orig_cur == new_currency:
            product.price_display = orig
        elif orig_cur == "PKR" and new_currency == "USD":
            product.price_display = round(orig / exchange_rate, 2)
        elif orig_cur == "USD" and new_currency == "PKR":
            product.price_display = round(orig * exchange_rate, 2)
        elif orig_cur == "AED" and new_currency == "PKR":
            # AED → USD → PKR  (1 AED ≈ 0.2723 USD)
            usd_val = orig * 0.2723
            product.price_display = round(usd_val * exchange_rate, 2)
        elif orig_cur == "AED" and new_currency == "USD":
            product.price_display = round(orig * 0.2723, 2)
        else:
            product.price_display = orig  # fallback: no conversion

        product.currency_display = new_currency

    await db.commit()
    for product in products:
        await db.refresh(product)

    return products


# ---------------------------------------------------------------------------
# ExchangeRateCache CRUD
# ---------------------------------------------------------------------------
async def save_exchange_rate(
    db: AsyncSession,
    base: str,
    target: str,
    rate: float,
    source: str,
) -> ExchangeRateCache:
    """Persist a fresh exchange rate to the DB cache (Tier 2)."""
    entry = ExchangeRateCache(
        base_currency=base,
        target_currency=target,
        rate=rate,
        fetched_at=datetime.now(timezone.utc),
        source=source,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_cached_exchange_rate(
    db: AsyncSession,
    base: str,
    target: str,
    max_age_hours: int = 1,
) -> Optional[ExchangeRateCache]:
    """
    Return the most recent cached rate that is younger than max_age_hours.
    Returns None if no fresh cache exists.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    result = await db.execute(
        select(ExchangeRateCache)
        .where(
            ExchangeRateCache.base_currency == base,
            ExchangeRateCache.target_currency == target,
            ExchangeRateCache.fetched_at >= cutoff,
        )
        .order_by(ExchangeRateCache.fetched_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
