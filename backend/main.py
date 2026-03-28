"""
main.py — FastAPI application for the Explainable AI Shopping Assistant.

Endpoints:
  POST /api/query            — New search (streams SSE events) or resume from interrupt
  POST /api/followup         — Follow-up question with conversation memory
  POST /api/switch-currency  — Re-convert prices (no re-scraping, no LLM)
  GET  /api/products/all     — All products (included + excluded) for a session
  GET  /api/exchange-rate    — Current cached exchange rate
  GET  /api/demo-sessions    — List pre-seeded demo sessions
  POST /api/seed-demo        — Trigger demo data seeding
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from langgraph.types import Command

from config import settings
from database.connection import init_db, get_db, async_session_maker
from database import crud
from database.models import SearchSession, Product
from models.schemas import (
    SearchRequest,
    FollowUpRequest,
    CurrencySwitchRequest,
    ExchangeRateInfo,
    DemoSession,
)
from services.currency_service import get_exchange_rate
from services.input_gate import evaluate_input_gate
from graph.workflow import shopping_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: create tables in Supabase on startup
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — creating tables in Supabase if needed...")
    await init_db()
    logger.info("Database initialised.")
    yield
    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ShopBuddy",
    description="Explainable AI-Powered Shopping Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: build the initial state dict for a new query
# ---------------------------------------------------------------------------
def _build_initial_state(query: str, display_currency: str, model: str = "gemini-3-flash-preview") -> dict:
    return {
        "user_query": query,
        "display_currency": display_currency,
        "model": model,
        "conversation_history": [],
        "search_terms": [],
        "budget_max": None,
        "budget_currency": display_currency,
        "min_reviews": settings.DEFAULT_MIN_REVIEWS,
        "category_hint": "",
        "exchange_rate_usd_to_pkr": settings.FALLBACK_USD_TO_PKR,
        "exchange_rate_timestamp": "",
        "exchange_rate_source": "pending",
        "daraz_products": [],
        "amazon_products": [],
        "all_products": [],
        "product_reviews": {},
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


# ---------------------------------------------------------------------------
# Shared helper: convert a Product ORM row to a complete response dict
# ---------------------------------------------------------------------------
def _product_to_dict(p: Product) -> dict:
    """Serialize a Product ORM instance to a dict with ALL fields."""
    return {
        "id": str(p.id),
        "source": p.source,
        "name": p.name,
        "price_original": p.price_original,
        "currency_original": p.currency_original,
        "price_display": p.price_display,
        "currency_display": p.currency_display,
        "rating": p.rating,
        "review_count": p.review_count,
        "product_url": p.product_url,
        "image_url": p.image_url,
        "discount_percentage": p.discount_percentage,
        "brand": p.brand,
        "value_score": p.value_score,
        "recommendation_badge": p.recommendation_badge,
        "reasoning_chain": p.reasoning_chain,
        "cross_platform_note": p.cross_platform_note,
        "filter_status": p.filter_status,
        "filter_reason": p.filter_reason,
        "filter_name": p.filter_name,
        "review_sentiment": p.review_sentiment,
        "review_positive_themes": p.review_positive_themes,
        "review_negative_themes": p.review_negative_themes,
        "review_summary": p.review_summary,
    }


# ---------------------------------------------------------------------------
# Helper: load a session's full result from Supabase (all enriched DB fields)
# ---------------------------------------------------------------------------
async def _load_session_result(session_id: str, db: AsyncSession, extra: dict | None = None) -> dict:
    """
    Read all products for a session from Supabase and build the complete
    response payload.  DB rows always have review data and reasoning chains
    that the in-memory pipeline state may not carry.
    """
    from database.models import SearchSession as SS
    session = await db.get(SS, session_id)
    included = await crud.get_products_by_session(db, session_id, filter_status="included")
    excluded = await crud.get_products_by_session(db, session_id, filter_status="excluded")
    result = {
        "session_id": session_id,
        "ranked_products": [_product_to_dict(p) for p in included],
        "excluded_products": [_product_to_dict(p) for p in excluded],
        "funnel_stats": (session.funnel_stats or {}) if session else {},
        "fetch_explanation": (session.fetch_explanation or "") if session else "",
    }
    if extra:
        result.update(extra)
    return result


async def _load_demo_result(session: SearchSession, db: AsyncSession) -> dict:
    """Load all data for a pre-seeded demo session from Supabase."""
    result = await _load_session_result(str(session.id), db)
    result.update({
        "query": session.query,
        "display_currency": session.display_currency,
        "exchange_rate": session.exchange_rate_used,
        "is_demo": True,
    })
    return result


# ---------------------------------------------------------------------------
# POST /api/query — New search or resume from interrupt
# ---------------------------------------------------------------------------
@app.post("/api/query")
async def query_endpoint(request: SearchRequest):
    """
    Accepts a search query and streams SSE events as the pipeline progresses.

    If the query matches a pre-seeded demo session in Supabase, returns
    the cached result instantly without calling external APIs.

    Query params in body:
      - query: str
      - display_currency: "PKR" or "USD"
      - thread_id: str | None (to resume from interrupt)
      - approved: bool | None (to approve/reject interrupt)
    """
    query = request.query.strip()
    display_currency = request.display_currency
    model = request.model

    # --- Check for thread_id and approved fields (resume from interrupt) ---
    body = request.model_dump()
    thread_id = body.get("thread_id")
    approved = body.get("approved")

    if thread_id is not None and approved is not None:
        # Resuming from a keyword-confirmation interrupt
        async def _resume_stream():
            config = {"configurable": {"thread_id": thread_id}}
            try:
                async for event in shopping_graph.astream_events(
                    Command(resume={"approved": approved}),
                    config=config,
                    version="v2",
                ):
                    kind = event.get("event", "")
                    if kind == "on_chain_end" and event.get("name") in (
                        "scraper", "filter", "analyzer", "reviewer", "explainer"
                    ):
                        yield {
                            "event": "step_complete",
                            "data": json.dumps({
                                "step": event["name"],
                                "status": "done",
                            }),
                        }

                # Use in-memory state — it has the correct filter decisions and
                # excluded_products list.  The only data missing from the product
                # dicts is review fields (stored separately in review_insights),
                # so we merge those in before sending.
                final = await shopping_graph.aget_state(config)
                ranked = list(final.values.get("ranked_products", []))
                excluded = list(final.values.get("excluded_products", []))
                review_insights = final.values.get("review_insights", {})
                rec_explanations = final.values.get("recommendation_explanations", {})

                # Merge review data + reasoning chains into each ranked product dict.
                # - review_insights: stored separately by reviewer_node (not in product dicts)
                # - rec_explanations: explainer modifies ranked in-place but doesn't return
                #   ranked_products in its state update, so the checkpoint lacks reasoning_chain
                for p in ranked:
                    pid = p.get("id", "")
                    if pid in review_insights:
                        ins = review_insights[pid]
                        p["review_sentiment"] = ins.get("sentiment_score")
                        p["review_positive_themes"] = ins.get("positive_themes", [])
                        p["review_negative_themes"] = ins.get("negative_themes", [])
                        p["review_summary"] = ins.get("review_summary", "")
                    if pid in rec_explanations:
                        card = rec_explanations[pid]
                        p["reasoning_chain"] = card.get("reasoning_chain", [])
                        if card.get("cross_platform_note"):
                            p["cross_platform_note"] = card["cross_platform_note"]

                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "session_id": final.values.get("session_id", ""),
                        "ranked_products": ranked,
                        "excluded_products": excluded,
                        "funnel_stats": final.values.get("funnel_stats", {}),
                        "fetch_explanation": final.values.get("fetch_explanation", ""),
                        "recommendation_explanations": rec_explanations,
                        "errors": final.values.get("errors", []),
                    }),
                }
            except Exception as exc:
                yield {"event": "error", "data": json.dumps({"error": str(exc)})}

        return EventSourceResponse(_resume_stream())

    # --- Input gate: block unsafe/off-topic prompts before any agent work ---
    gate = await evaluate_input_gate(query, model)
    if not gate.get("allowed", False):
        async def _blocked_stream():
            yield {
                "event": "blocked",
                "data": json.dumps({
                    "message": gate.get("message"),
                    "reason": gate.get("reason", "blocked_by_gate"),
                }),
            }

        return EventSourceResponse(_blocked_stream())

    # --- Check Supabase for a demo session matching this query ---
    try:
        async with async_session_maker() as db:
            result = await db.execute(
                select(SearchSession).where(
                    SearchSession.query.ilike(query),
                    SearchSession.is_demo == True,  # noqa: E712
                )
            )
            demo_session = result.scalar_one_or_none()

            if demo_session:
                logger.info("Demo hit for '%s' — loading from Supabase", query)
                demo_result = await _load_demo_result(demo_session, db)
                # Return as a single SSE event for consistency
                async def _demo_stream():
                    yield {"event": "complete", "data": json.dumps(demo_result)}
                return EventSourceResponse(_demo_stream())
    except Exception as exc:
        logger.warning("Demo lookup failed: %s — running live pipeline", exc)

    # --- Run the full LangGraph pipeline ---
    thread_id = str(uuid4())

    async def _live_stream():
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = _build_initial_state(query, display_currency, model)

        try:
            # Phase 1: run until the interrupt (keyword confirmation)
            async for event in shopping_graph.astream_events(
                initial_state, config=config, version="v2",
            ):
                kind = event.get("event", "")
                if kind == "on_chain_end" and event.get("name") == "supervisor":
                    yield {
                        "event": "step_complete",
                        "data": json.dumps({"step": "supervisor", "status": "done"}),
                    }

            # Check if graph is interrupted
            graph_state = await shopping_graph.aget_state(config)

            if graph_state.next:
                # Graph is paused at keyword_confirmation — send interrupt event
                vals = graph_state.values
                yield {
                    "event": "interrupt",
                    "data": json.dumps({
                        "thread_id": thread_id,
                        "search_terms": vals.get("search_terms", []),
                        "budget_max": vals.get("budget_max"),
                        "budget_currency": vals.get("budget_currency", display_currency),
                        "message": "Confirm these search parameters to proceed.",
                    }),
                }
            else:
                # No interrupt — graph completed (shouldn't happen in normal flow)
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "session_id": graph_state.values.get("session_id", ""),
                        "ranked_products": graph_state.values.get("ranked_products", []),
                        "errors": graph_state.values.get("errors", []),
                    }),
                }

        except Exception as exc:
            logger.error("Pipeline error: %s", exc)
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(_live_stream())


# ---------------------------------------------------------------------------
# POST /api/followup — Follow-up question answered by LLM using session context
# ---------------------------------------------------------------------------
@app.post("/api/followup")
async def followup_endpoint(request: FollowUpRequest):
    """
    Answer a follow-up question about the current session's products.
    Uses the LLM directly with session context — does NOT re-run the pipeline.
    """
    thread_id = request.thread_id
    query = request.query.strip()
    display_currency = request.display_currency
    model_name = request.model

    # --- Input gate for follow-up prompts as well ---
    gate = await evaluate_input_gate(query, model_name)
    if not gate.get("allowed", False):
        async def _blocked_followup_stream():
            yield {
                "event": "blocked",
                "data": json.dumps({
                    "message": gate.get("message"),
                    "reason": gate.get("reason", "blocked_by_gate"),
                }),
            }

        return EventSourceResponse(_blocked_followup_stream())

    async def _followup_stream():
        try:
            # Load session data from Supabase
            async with async_session_maker() as db:
                session = await crud.get_search_session(db, thread_id)
                if not session:
                    yield {"event": "error", "data": json.dumps({"error": "Session not found"})}
                    return

                included = await crud.get_products_by_session(db, session.id, filter_status="included")
                excluded = await crud.get_products_by_session(db, session.id, filter_status="excluded")

            # Build product context for the LLM
            product_lines = []
            for i, p in enumerate(included, 1):
                product_lines.append(
                    f"#{i}: {p.name}\n"
                    f"  Source: {p.source}, Price: {p.price_display:.0f} {p.currency_display}\n"
                    f"  Rating: {p.rating}/5, Reviews: {p.review_count}\n"
                    f"  Badge: {p.recommendation_badge or 'none'}\n"
                    f"  Value Score: {p.value_score or 0:.4f}\n"
                    f"  Brand: {p.brand or 'Unknown'}"
                )
                if p.reasoning_chain:
                    reasons = p.reasoning_chain if isinstance(p.reasoning_chain, list) else []
                    product_lines[-1] += "\n  Reasoning: " + "; ".join(reasons)
                if p.review_summary:
                    product_lines[-1] += f"\n  Review Summary: {p.review_summary}"
                if p.cross_platform_note:
                    product_lines[-1] += f"\n  Cross-Platform: {p.cross_platform_note}"

            products_text = "\n\n".join(product_lines) or "No products available."

            excluded_summary = ""
            if excluded:
                excluded_lines = [
                    f"- {p.name} ({p.source}): {p.filter_reason or 'filtered out'}"
                    for p in excluded[:10]
                ]
                excluded_summary = f"\n\nExcluded products:\n" + "\n".join(excluded_lines)

            prompt = f"""You are a helpful shopping assistant. The user previously searched for products and received recommendations. Now they have a follow-up question.

Original search: "{session.query}"
Display currency: {display_currency}

Recommended products:
{products_text}
{excluded_summary}

Fetch explanation: {session.fetch_explanation or 'N/A'}

User's follow-up question: "{query}"

Answer the question clearly and concisely based on the product data above. Reference specific products by name, mention actual numbers (prices, ratings, scores) when comparing. If the user asks about a product not in the list, say so. Keep your answer conversational and helpful."""

            # Get the LLM and generate response
            from agents.supervisor import _get_llm, _extract_text
            active_llm = _get_llm(model_name)
            from langchain_core.messages import HumanMessage
            response = await active_llm.ainvoke([HumanMessage(content=prompt)])
            answer = _extract_text(response.content).strip()

            yield {
                "event": "complete",
                "data": json.dumps({
                    "response": answer,
                    "session_id": str(session.id),
                }),
            }

        except Exception as exc:
            logger.error("Follow-up error: %s", exc)
            yield {"event": "error", "data": json.dumps({"error": str(exc)})}

    return EventSourceResponse(_followup_stream())


# ---------------------------------------------------------------------------
# POST /api/switch-currency — Re-convert prices (pure DB + math, no LLM)
# ---------------------------------------------------------------------------
@app.post("/api/switch-currency")
async def switch_currency_endpoint(
    request: CurrencySwitchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Re-convert all product prices in a session to a new display currency."""
    thread_id = request.thread_id
    new_currency = request.display_currency

    # thread_id == session_id by convention
    session = await crud.get_search_session(db, thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get current exchange rate
    rate_info = await get_exchange_rate(db)

    # Re-convert prices in Supabase
    updated_products = await crud.update_product_prices(
        db, session.id, new_currency, rate_info["usd_to_pkr"]
    )

    included = [p for p in updated_products if p.filter_status == "included"]
    excluded = [p for p in updated_products if p.filter_status == "excluded"]

    return {
        "ranked_products": [_product_to_dict(p) for p in included],
        "excluded_products": [_product_to_dict(p) for p in excluded],
        "exchange_rate": {
            "usd_to_pkr": rate_info["usd_to_pkr"],
            "pkr_to_usd": rate_info["pkr_to_usd"],
            "source": rate_info["source"],
        },
        "display_currency": new_currency,
    }


# ---------------------------------------------------------------------------
# GET /api/products/all — All products for a session
# ---------------------------------------------------------------------------
@app.get("/api/products/all")
async def get_all_products(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return ALL products (included + excluded) for a session with filter audit trail."""
    products = await crud.get_products_by_session(db, thread_id)
    if not products:
        raise HTTPException(status_code=404, detail="No products found for this session")

    return {
        "session_id": thread_id,
        "total": len(products),
        "products": [_product_to_dict(p) for p in products],
    }


# ---------------------------------------------------------------------------
# GET /api/exchange-rate — Current exchange rate
# ---------------------------------------------------------------------------
@app.get("/api/exchange-rate", response_model=ExchangeRateInfo)
async def get_exchange_rate_endpoint(db: AsyncSession = Depends(get_db)):
    """Return the current cached USD↔PKR exchange rate."""
    rate_info = await get_exchange_rate(db)
    return ExchangeRateInfo(
        usd_to_pkr=rate_info["usd_to_pkr"],
        pkr_to_usd=rate_info["pkr_to_usd"],
        last_updated=rate_info["fetched_at"],
        source=rate_info["source"],
    )


# ---------------------------------------------------------------------------
# GET /api/demo-sessions — List pre-seeded demo sessions
# ---------------------------------------------------------------------------
@app.get("/api/demo-sessions")
async def get_demo_sessions_endpoint(db: AsyncSession = Depends(get_db)):
    """Return all sessions flagged as demo for the 'Try a demo' UI."""
    sessions = await crud.get_demo_sessions(db)
    return [
        DemoSession(
            session_id=str(s.id),
            query=s.query,
            display_currency=s.display_currency,
            product_count=len(s.products) if s.products else 0,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in sessions
    ]


# ---------------------------------------------------------------------------
# POST /api/seed-demo — Trigger demo data seeding
# ---------------------------------------------------------------------------
@app.post("/api/seed-demo")
async def seed_demo_endpoint():
    """
    Run the full pipeline for 3 demo queries and save to Supabase.
    Call this ONCE before the hackathon demo.
    """
    from database.seed_demo import seed_demo_data
    results = await seed_demo_data()
    return {
        "status": "success",
        "sessions_created": len([r for r in results if r["status"] == "success"]),
        "details": results,
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "ShopBuddy"}
