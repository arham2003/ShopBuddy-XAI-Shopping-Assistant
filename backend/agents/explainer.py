"""
agents/explainer.py — Generates all final human-readable explanations.

Produces TWO types of explanation:
  Type A — Fetch Explanation (Layer 1): WHY certain products were included/excluded
  Type B — Recommendation Explanation (Layer 2): WHY each top product is ranked where it is

BUG FIX: ChatGoogleGenerativeAI returns response.content as a list of parts
(not a plain string) for Gemini 3 models. _extract_text() handles both cases.
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from config import settings
from database.connection import async_session_maker
from graph.state import ShoppingState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM instances — all three models available for testing
# ---------------------------------------------------------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=1.0,
    max_retries=2,
    google_api_key=settings.GOOGLE_API_KEY,
)

llm_llama70b = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=1.0,
    max_tokens=32768,
    groq_api_key=settings.GROQ_API_KEY,
)

llm_llama8b = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=1.0,
    max_tokens=128000,
    groq_api_key=settings.GROQ_API_KEY,
)


def _get_llm(model_name: str):
    """Return the LLM instance matching the requested model name."""
    if model_name == "llama-3.3-70b-versatile":
        return llm_llama70b
    if model_name == "llama-3.1-8b-instant":
        return llm_llama8b
    return llm
# ---------------------------------------------------------------------------
# Helper: safely extract text from Gemini response content (str or list)
# ---------------------------------------------------------------------------
def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text", ""))
        return "".join(parts)
    return str(content)


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```[a-z]*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Type A — Fetch Explanation
# ---------------------------------------------------------------------------
async def _generate_fetch_explanation(state: ShoppingState, active_llm=None) -> str:
    """Transparency report explaining the entire fetch-and-filter pipeline."""
    funnel = state.get("funnel_stats", {})
    search_terms = state.get("search_terms", [])
    rate = state.get("exchange_rate_usd_to_pkr", 278.0)
    rate_source = state.get("exchange_rate_source", "fallback")
    display_currency = state.get("display_currency", "PKR")
    filter_log = state.get("filter_log", [])

    # Summarise removals (cap at 15 to avoid huge prompts)
    removals = [f for f in filter_log if f.get("decision") == "fail"][:15]
    removal_summary = "\n".join(
        f"- {r['product_name']} ({r['product_source']}): {r['reason']}"
        for r in removals
    ) or "None"

    prompt = f"""Generate a concise transparency report for a shopping search.

Search terms: {', '.join(search_terms)}
Display currency: {display_currency}
Exchange rate: 1 USD = {rate:.2f} PKR (source: {rate_source})

Funnel:
- Fetched: {funnel.get('total_fetched', 0)} total ({funnel.get('daraz_count', 0)} Daraz, {funnel.get('amazon_count', 0)} Amazon)
- After relevance/brand filter: {funnel.get('after_relevance_filter', 0)}
- After budget filter: {funnel.get('after_budget_filter', 0)}
- After reviews filter: {funnel.get('after_review_filter', 0)}
- After duplicate removal: {funnel.get('after_duplicate_filter', 0)}
- Total removed: {funnel.get('total_removed', 0)}

Notable exclusions:
{removal_summary}

Write a 3-5 sentence transparency report explaining:
1. Where products were sourced and how many were found
2. How many were filtered out and the main reasons (in plain language)
3. The exchange rate used and its reliability
Keep it conversational, helpful, and factual. No markdown headers.
"""
    active_llm = active_llm or llm
    try:
        response = await active_llm.ainvoke([HumanMessage(content=prompt)])
        return _extract_text(response.content).strip()
    except Exception as exc:
        logger.error("Fetch explanation LLM call failed: %s", exc)
        return (
            f"We searched Daraz.pk and Amazon for '{', '.join(search_terms)}' and found "
            f"{funnel.get('total_fetched', 0)} products ({funnel.get('daraz_count', 0)} from Daraz, "
            f"{funnel.get('amazon_count', 0)} from Amazon). After applying budget, review count, "
            f"trust, and relevance filters, {funnel.get('after_duplicate_filter', 0)} products "
            f"remained. Exchange rate used: 1 USD = {rate:.2f} PKR (source: {rate_source})."
        )


# ---------------------------------------------------------------------------
# Type B — Recommendation Explanations
# ---------------------------------------------------------------------------
async def _generate_recommendation_explanations(state: ShoppingState, active_llm=None) -> dict:
    """Per-product explanation cards for the top 5 ranked products."""
    ranked = state.get("ranked_products", [])[:5]
    review_insights = state.get("review_insights", {})
    explanations: dict[str, dict] = {}

    if not ranked:
        return explanations

    product_summaries = []
    for i, p in enumerate(ranked, 1):
        pid = p.get("id", "")
        ri = review_insights.get(pid, {})
        product_summaries.append(
            f"#{i}: {p.get('name', 'Unknown')}\n"
            f"  Source: {p.get('source')}, Price: {p.get('price_display', 0):.0f} {p.get('currency_display', 'PKR')}\n"
            f"  Rating: {p.get('rating', 0)}/5, Reviews: {p.get('review_count', 0)}\n"
            f"  Value Score: {p.get('value_score', 0):.4f}\n"
            f"  Badge: {p.get('recommendation_badge', 'none')}\n"
            f"  Sentiment: {ri.get('sentiment_score', 'N/A')}\n"
            f"  Cross-Platform: {p.get('cross_platform_note', 'N/A')}"
        )

    products_text = "\n\n".join(product_summaries)

    prompt = f"""For each top-ranked product below, generate a concise explanation card.

{products_text}

Return ONLY a JSON array — one object per product in order, no extra text:
[
  {{
    "product_index": 1,
    "recommendation_badge": "Best Overall",
    "confidence_score": 0.85,
    "reasoning_chain": [
      "Highest value score of 12.34 across all results",
      "Strong 4.5/5 rating from 850+ verified reviews",
      "Price of 45,000 PKR offers excellent quality-to-price ratio"
    ],
    "trade_offs": "Slightly heavier than budget alternatives.",
    "cross_platform_note": null
  }}
]

For reasoning_chain: 3-4 bullet points explaining step-by-step WHY this product earned its rank.
Be specific — mention actual numbers (scores, ratings, prices).
"""
    active_llm = active_llm or llm
    try:
        response = await active_llm.ainvoke([HumanMessage(content=prompt)])
        raw = _clean_json(_extract_text(response.content))
        cards = json.loads(raw)
    except Exception as exc:
        logger.error("Recommendation explanation LLM call failed: %s", exc)
        # Fallback: generate basic cards without LLM
        cards = [
            {
                "product_index": i + 1,
                "recommendation_badge": p.get("recommendation_badge", ""),
                "confidence_score": 0.5,
                "reasoning_chain": [
                    f"Value score: {p.get('value_score', 0):.4f}",
                    f"Rating: {p.get('rating', 0)}/5 with {p.get('review_count', 0)} reviews",
                    f"Price: {p.get('price_display', 0):.0f} {p.get('currency_display', 'PKR')}",
                ],
                "trade_offs": "Detailed analysis unavailable.",
                "cross_platform_note": p.get("cross_platform_note"),
            }
            for i, p in enumerate(ranked)
        ]

    # Map cards back to product IDs and update reasoning_chain in ranked list
    for card in cards:
        idx = card.get("product_index", 1) - 1
        if 0 <= idx < len(ranked):
            pid = ranked[idx].get("id", "")
            explanations[pid] = card
            ranked[idx]["reasoning_chain"] = card.get("reasoning_chain", [])

    return explanations


# ---------------------------------------------------------------------------
# Graph node function
# ---------------------------------------------------------------------------
async def explainer_node(state: ShoppingState) -> dict:
    """
    LangGraph node: generates both layers of explainability and persists to Supabase.
    """
    errors: list[str] = list(state.get("errors", []))
    model_name = state.get("model", "gemini-3-flash-preview")
    active_llm = _get_llm(model_name)

    # --- Type A: Fetch explanation ---
    fetch_explanation = await _generate_fetch_explanation(state, active_llm)

    # --- Type B: Recommendation explanations ---
    rec_explanations = await _generate_recommendation_explanations(state, active_llm)

    # --- Persist to Supabase ---
    try:
        async with async_session_maker() as db:
            session_id = state.get("session_id", "")
            if session_id:
                from database.models import SearchSession, Product
                from sqlalchemy import select

                # Update session with fetch explanation and funnel stats
                session = await db.get(SearchSession, session_id)
                if session:
                    session.fetch_explanation = fetch_explanation
                    session.funnel_stats = state.get("funnel_stats", {})

                # Update product reasoning chains
                result_db = await db.execute(
                    select(Product).where(Product.session_id == session_id)
                )
                db_products = {str(p.id): p for p in result_db.scalars().all()}
                for pid, card in rec_explanations.items():
                    if pid in db_products:
                        db_products[pid].reasoning_chain = card.get("reasoning_chain", [])

                await db.commit()
                logger.info("Persisted explanations to Supabase for session %s", session_id)
    except Exception as exc:
        logger.error("Failed to persist explanations to Supabase: %s", exc)
        errors.append(f"DB explanation save failed: {exc}")

    return {
        "fetch_explanation": fetch_explanation,
        "recommendation_explanations": rec_explanations,
        "current_step": "explainer_done",
        "errors": errors,
    }
