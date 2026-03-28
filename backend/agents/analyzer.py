"""
agents/analyzer.py — Pure-Python product ranking (no LLM).

Ranks filtered products by value score, assigns badges, and caps to top 5.
No LLM calls — fully deterministic.
"""

from __future__ import annotations

import logging
import math

from database.connection import async_session_maker
from graph.state import ShoppingState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure Python: Calculate value scores
# ---------------------------------------------------------------------------
def _calculate_value_scores(products: list[dict]) -> list[dict]:
    for p in products:
        rating = float(p.get("rating", 0))
        reviews = int(p.get("review_count", 0))
        price = float(p.get("price_display", 1))
        if price <= 0:
            price = 1
        p["value_score"] = round((rating * math.log2(reviews + 1)) / (price / 1000), 4)
    products.sort(key=lambda x: x.get("value_score", 0), reverse=True)
    return products


# ---------------------------------------------------------------------------
# Pure Python: Assign recommendation badges
# ---------------------------------------------------------------------------
def _assign_badges(products: list[dict]) -> list[dict]:
    if not products:
        return products

    products[0]["recommendation_badge"] = "Best Overall"

    remaining = [p for p in products if not p.get("recommendation_badge")]
    if remaining:
        cheapest = min(remaining, key=lambda x: x.get("price_display", float("inf")))
        cheapest["recommendation_badge"] = "Best Budget"

    remaining = [p for p in products if not p.get("recommendation_badge")]
    if remaining:
        top_rated = max(remaining, key=lambda x: (x.get("rating", 0), x.get("review_count", 0)))
        top_rated["recommendation_badge"] = "Best Rated"

    return products


# ---------------------------------------------------------------------------
# Graph node function
# ---------------------------------------------------------------------------
async def analyzer_node(state: ShoppingState) -> dict:
    """
    LangGraph node: ranks filtered products, assigns badges, persists to Supabase.
    Pure Python — no LLM calls.
    """
    filtered = state.get("filtered_products", [])
    errors: list[str] = list(state.get("errors", []))

    if not filtered:
        return {"ranked_products": [], "current_step": "analyzer_done", "errors": errors}

    ranked = _assign_badges(_calculate_value_scores(list(filtered)))
    ranked = ranked[:5]

    try:
        async with async_session_maker() as db:
            session_id = state.get("session_id", "")
            if session_id:
                from database.models import Product
                from sqlalchemy import select
                result_db = await db.execute(
                    select(Product).where(Product.session_id == session_id)
                )
                db_products = {str(p.id): p for p in result_db.scalars().all()}
                for rp in ranked:
                    pid = rp.get("id", "")
                    if pid in db_products:
                        db_products[pid].value_score = rp.get("value_score")
                        db_products[pid].recommendation_badge = rp.get("recommendation_badge")
                        db_products[pid].cross_platform_note = rp.get("cross_platform_note")
                await db.commit()
    except Exception as exc:
        logger.error("Failed to update rankings in Supabase: %s", exc)
        errors.append(f"DB ranking update failed: {exc}")

    return {"ranked_products": ranked, "current_step": "analyzer_done", "errors": errors}
