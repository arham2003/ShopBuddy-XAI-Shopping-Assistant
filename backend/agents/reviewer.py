"""
agents/reviewer.py — Deep-dives into reviews for the top-ranked products.

For each of the top 3–5 products, extracts review text (from the scraper's
enriched data) and sends it to the LLM for sentiment analysis, theme
extraction, and trust scoring.

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
from tools.review_extractor import compute_basic_sentiment
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

TOP_N = 5


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
# LLM review analysis
# ---------------------------------------------------------------------------
async def _analyze_reviews_with_llm(product_name: str, review_text: str, active_llm=None) -> dict:
    """Send review text to the LLM for structured sentiment analysis."""
    prompt = f"""Analyze these customer reviews for "{product_name}".

Reviews:
{review_text[:3000]}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "sentiment_score": 0.75,
  "positive_themes": ["good battery life", "easy to use"],
  "negative_themes": ["expensive"],
  "review_summary": "Two-sentence summary of customer experience.",
  "trust_score": 0.8
}}

Guidelines:
- sentiment_score: 0.0 (very negative) to 1.0 (very positive)
- positive_themes: 2-4 recurring positive themes
- negative_themes: 1-3 recurring negative themes (empty list [] if none)
- trust_score: 0.0 (suspicious reviews) to 1.0 (high quality, specific reviews)
"""
    active_llm = active_llm or llm
    try:
        response = await active_llm.ainvoke([HumanMessage(content=prompt)])
        raw = _clean_json(_extract_text(response.content))
        return json.loads(raw)
    except Exception as exc:
        logger.warning("Review LLM analysis failed for '%s': %s", product_name, exc)
        return {
            "sentiment_score": compute_basic_sentiment(review_text),
            "positive_themes": [],
            "negative_themes": [],
            "review_summary": "Automated review analysis unavailable.",
            "trust_score": 0.5,
        }


# ---------------------------------------------------------------------------
# Graph node function
# ---------------------------------------------------------------------------
async def reviewer_node(state: ShoppingState) -> dict:
    """
    LangGraph node: analyses reviews for the top-ranked products.
    Populates review_insights and updates Supabase with review data.
    """
    ranked = state.get("ranked_products", [])
    product_reviews = state.get("product_reviews", {})
    model_name = state.get("model", "gemini-3-flash-preview")
    active_llm = _get_llm(model_name)
    errors: list[str] = list(state.get("errors", []))

    review_insights: dict[str, dict] = {}

    for product in ranked[:TOP_N]:
        pid = product.get("id", "")
        pname = product.get("name", "Unknown")

        # Look up pre-extracted reviews by product name
        reviews = product_reviews.get(pname.lower(), [])

        if reviews:
            review_text = "\n---\n".join(r["text"] for r in reviews)
            insight = await _analyze_reviews_with_llm(pname, review_text, active_llm)
        else:
            insight = {
                "sentiment_score": 0.5,
                "positive_themes": [],
                "negative_themes": [],
                "review_summary": "No customer reviews available for analysis.",
                "trust_score": 0.5,
            }

        review_insights[pid] = {"product_id": pid, **insight}

    # --- Persist review insights to Supabase ---
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
                for pid, insight in review_insights.items():
                    if pid in db_products:
                        db_products[pid].review_sentiment = insight.get("sentiment_score")
                        db_products[pid].review_positive_themes = insight.get("positive_themes")
                        db_products[pid].review_negative_themes = insight.get("negative_themes")
                        db_products[pid].review_summary = insight.get("review_summary")
                await db.commit()
    except Exception as exc:
        logger.error("Failed to persist review insights to Supabase: %s", exc)
        errors.append(f"DB review update failed: {exc}")

    return {"review_insights": review_insights, "current_step": "reviewer_done", "errors": errors}
