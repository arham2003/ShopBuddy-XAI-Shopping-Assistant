"""
database/seed_demo.py — Pre-seeds Supabase with demo search sessions.

Run this ONCE before a hackathon demo to populate the database with
fully-processed search results. During the demo, these sessions load
instantly from Supabase without calling external APIs.

Usage:
    python -m database.seed_demo
    # or via the POST /api/seed-demo endpoint
"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from database.connection import init_db, async_session_maker
from database import crud

logger = logging.getLogger(__name__)

# Pre-defined demo queries
DEMO_QUERIES = [
    {"query": "best juicer blender under 5000 PKR", "display_currency": "PKR"},
    {"query": "wireless earbuds under 3000 PKR", "display_currency": "PKR"},
    {"query": "laptop stand for office", "display_currency": "USD"},
]


async def seed_demo_data() -> list[dict]:
    """
    Run the full LangGraph pipeline for each demo query and mark the
    resulting sessions with is_demo=True in Supabase.

    Returns a list of {"session_id": str, "query": str, "status": str} dicts.
    """
    # Lazy import to avoid circular dependency at module level
    from graph.workflow import shopping_graph

    await init_db()
    results: list[dict] = []

    for demo in DEMO_QUERIES:
        thread_id = str(uuid4())
        logger.info("Seeding demo: '%s' (thread=%s)", demo["query"], thread_id)

        try:
            # --- Phase 1: Run until the interrupt (keyword confirmation) ---
            config = {"configurable": {"thread_id": thread_id}}
            initial_state = {
                "user_query": demo["query"],
                "display_currency": demo["display_currency"],
                "conversation_history": [],
                "search_terms": [],
                "budget_max": None,
                "budget_currency": demo["display_currency"],
                "min_reviews": 5,
                "category_hint": "",
                "exchange_rate_usd_to_pkr": 278.0,
                "exchange_rate_timestamp": "",
                "exchange_rate_source": "pending",
                "daraz_products": [],
                "amazon_products": [],
                "all_products": [],
                "filtered_products": [],
                "excluded_products": [],
                "filter_log": [],
                "funnel_stats": {},
                "ranked_products": [],
                "review_insights": {},
                "fetch_explanation": "",
                "recommendation_explanations": {},
                "session_id": "",
                "current_step": "start",
                "errors": [],
            }

            # First invocation runs until interrupt
            await shopping_graph.ainvoke(initial_state, config=config)

            # --- Phase 2: Resume past the interrupt (auto-approve) ---
            from langgraph.types import Command
            final_state = await shopping_graph.ainvoke(
                Command(resume={"approved": True}),
                config=config,
            )

            # --- Mark session as demo in Supabase ---
            session_id = final_state.get("session_id", "")
            if session_id:
                async with async_session_maker() as db:
                    session = await crud.get_search_session(db, session_id)
                    if session:
                        session.is_demo = True
                        await db.commit()
                        logger.info("Marked session %s as demo", session_id)

            results.append({
                "session_id": session_id,
                "query": demo["query"],
                "status": "success",
                "product_count": len(final_state.get("ranked_products", [])),
            })

        except Exception as exc:
            logger.error("Demo seeding failed for '%s': %s", demo["query"], exc)
            results.append({
                "session_id": "",
                "query": demo["query"],
                "status": f"error: {exc}",
                "product_count": 0,
            })

    return results


# ---------------------------------------------------------------------------
# CLI entry point:  python -m database.seed_demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    # Load env vars
    from dotenv import load_dotenv
    load_dotenv()

    results = asyncio.run(seed_demo_data())
    print("\n=== Demo Seeding Results ===")
    for r in results:
        print(f"  [{r['status']}] {r['query']} → session_id={r['session_id']} ({r['product_count']} products)")
