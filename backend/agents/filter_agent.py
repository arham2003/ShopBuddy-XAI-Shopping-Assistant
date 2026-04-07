"""
agents/filter_agent.py — The Explainability Engine (Layer 1).

Applies a progressive filter pipeline and logs EVERY inclusion/exclusion
decision with a human-readable reason. This is the core of the
"Fetch Explainability" layer.

Filter order:
  1. Relevance & Brand filter (LLM-powered) — runs FIRST to enforce brand/type matching
  2. Budget filter
  3. Minimum reviews filter (only when no budget is set)
  4. Duplicate detection (LLM-powered)

BUG FIX: ChatGoogleGenerativeAI returns response.content as a list of parts
(not a plain string) for Gemini 3 models. _extract_text() handles both cases.
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
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
    """
    ChatGoogleGenerativeAI may return .content as either:
      - str  (simple text response)
      - list (multimodal parts: [{"type": "text", "text": "..."}, ...])
    Always returns a plain string.
    """
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
    """Strip markdown code fences from LLM JSON responses."""
    text = text.strip()
    text = re.sub(r'^```[a-z]*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    return text.strip()


_RELEVANCE_SYSTEM_PROMPT = """You are a strict product relevance checker for e-commerce search.

Your task is ONLY to classify whether each candidate product is relevant to the user search intent.

Rules:
1) BRAND PRIORITY:
    - If the query mentions a specific brand, ONLY products from that exact brand are relevant.
2) PRODUCT-TYPE PRIORITY:
    - Product must match the core requested product type.
    - Accessories/parts/unrelated products are irrelevant.
3) DO NOT USE PRICE OR BUDGET FOR RELEVANCE:
    - Ignore product price completely in this stage.
    - Budget filtering is handled separately by deterministic logic.
4) ORDER LOCK:
    - Return exactly one verdict per input product, in the same order.
5) NO HALLUCINATION:
    - Use only provided search terms and product names.
    - Do not invent products, brands, or specs.

Return ONLY a JSON array of objects:
[
  {"name": "exact name", "relevant": true, "reason": "short reason"}
]
"""


_DUPLICATE_SYSTEM_PROMPT = """You are a strict cross-platform duplicate matcher.

Task:
- Find TRUE duplicates between Daraz and Amazon lists.
- Duplicate means same brand + same model/product identity.

Rules:
1) Different brands are NEVER duplicates.
2) Similar category alone is NOT enough.
3) Ignore price when deciding duplicates (price is used later only to choose cheaper listing).
4) Use only given lists and indexes.

Return ONLY a JSON array:
[
  {"daraz_index": 0, "amazon_index": 2, "reason": "same model"}
]

Return [] if no true duplicates.
"""


# ---------------------------------------------------------------------------
# Individual filter stages (pure Python — no LLM)
# ---------------------------------------------------------------------------
def _budget_filter(
    products: list[dict],
    budget_max: float | None,
    budget_currency: str,
    display_currency: str,
    log: list[dict],
) -> list[dict]:
    """Remove products that exceed the user's budget (with 10% margin)."""
    if budget_max is None:
        return products

    margin = budget_max * 1.10  # allow 10% above budget
    passed = []
    for p in products:
        try:
            price = float(p.get("price_display", 0) or 0)
        except (TypeError, ValueError):
            price = 0.0
        if price <= margin:
            log.append({
                "product_name": p["name"], "product_source": p["source"],
                "filter_name": "budget", "decision": "pass",
                "reason": f"{price:.0f} {display_currency} is within budget (+10% margin)",
                "threshold": f"{budget_max:.0f} {budget_currency} (+10% = {margin:.0f})",
                "actual_value": f"{price:.0f} {display_currency}",
            })
            passed.append(p)
        else:
            p["filter_status"] = "excluded"
            p["filter_reason"] = (
                f"{price:.0f} {display_currency} exceeds your budget of "
                f"{budget_max:.0f} {budget_currency} (even with 10% margin)"
            )
            p["filter_name"] = "budget"
            log.append({
                "product_name": p["name"], "product_source": p["source"],
                "filter_name": "budget", "decision": "fail",
                "reason": p["filter_reason"],
                "threshold": f"{budget_max:.0f} {budget_currency} (+10% = {margin:.0f})",
                "actual_value": f"{price:.0f} {display_currency}",
            })
    return passed


def _review_filter(
    products: list[dict],
    min_reviews: int,
    log: list[dict],
) -> list[dict]:
    """Remove products with too few reviews for reliable comparison."""
    passed = []
    for p in products:
        rc = p.get("review_count", 0)
        if rc >= min_reviews:
            log.append({
                "product_name": p["name"], "product_source": p["source"],
                "filter_name": "minimum_reviews", "decision": "pass",
                "reason": f"{rc} reviews meets the minimum of {min_reviews}",
                "threshold": str(min_reviews), "actual_value": str(rc),
            })
            passed.append(p)
        else:
            p["filter_status"] = "excluded"
            p["filter_reason"] = (
                f"Only {rc} reviews — minimum required is {min_reviews} "
                "for reliable comparison"
            )
            p["filter_name"] = "minimum_reviews"
            log.append({
                "product_name": p["name"], "product_source": p["source"],
                "filter_name": "minimum_reviews", "decision": "fail",
                "reason": p["filter_reason"],
                "threshold": str(min_reviews), "actual_value": str(rc),
            })
    return passed


# ---------------------------------------------------------------------------
# LLM-powered filter stages
# ---------------------------------------------------------------------------
async def _relevance_filter(
    products: list[dict],
    search_terms: list[str],
    log: list[dict],
    active_llm=None,
) -> list[dict]:
    """Use the LLM to check if each product is actually relevant to the query."""
    if not products:
        return products

    active_llm = active_llm or llm

    # Batch all names in one request to avoid many small API calls
    names = [p["name"] for p in products]
    terms_str = ", ".join(search_terms)

    user_payload = (
        f"User search terms: {terms_str}\n\n"
        f"Products to evaluate (0-indexed):\n{json.dumps(names, indent=2)}\n\n"
        "Return one verdict per product in the same order."
    )
    try:
        response = await active_llm.ainvoke([
            SystemMessage(content=_RELEVANCE_SYSTEM_PROMPT),
            HumanMessage(content=user_payload),
        ])
        raw = _clean_json(_extract_text(response.content))
        relevance_list = json.loads(raw)
    except Exception as exc:
        logger.warning("Relevance filter LLM call failed (%s) — keeping all products", exc)
        return products

    passed = []
    for i, p in enumerate(products):
        if i < len(relevance_list):
            entry = relevance_list[i]
            is_relevant = entry.get("relevant", True)
            reason = entry.get("reason", "")
        else:
            is_relevant = True
            reason = "no LLM verdict — kept by default"

        if is_relevant:
            log.append({
                "product_name": p["name"], "product_source": p["source"],
                "filter_name": "relevance", "decision": "pass",
                "reason": reason or "relevant to query",
                "threshold": "relevant to query", "actual_value": "relevant",
            })
            passed.append(p)
        else:
            p["filter_status"] = "excluded"
            p["filter_reason"] = f"Not relevant: {reason}"
            p["filter_name"] = "relevance"
            log.append({
                "product_name": p["name"], "product_source": p["source"],
                "filter_name": "relevance", "decision": "fail",
                "reason": f"Not relevant: {reason}",
                "threshold": "relevant to query", "actual_value": "irrelevant",
            })
    return passed


async def _duplicate_filter(
    products: list[dict],
    log: list[dict],
    active_llm=None,
) -> list[dict]:
    """Detect cross-platform duplicates and keep the cheaper listing."""
    daraz = [p for p in products if p["source"] == "daraz"]
    amazon = [p for p in products if p["source"] == "amazon"]

    if not daraz or not amazon:
        return products  # Nothing to compare cross-platform

    active_llm = active_llm or llm

    # Limit the list size to avoid huge prompts
    daraz_names = [d["name"][:80] for d in daraz[:20]]
    amazon_names = [a["name"][:80] for a in amazon[:20]]

    user_payload = (
        "Compare these lists and return TRUE duplicates.\n\n"
        f"Daraz (0-indexed):\n{json.dumps(daraz_names, indent=2)}\n\n"
        f"Amazon (0-indexed):\n{json.dumps(amazon_names, indent=2)}"
    )
    try:
        response = await active_llm.ainvoke([
            SystemMessage(content=_DUPLICATE_SYSTEM_PROMPT),
            HumanMessage(content=user_payload),
        ])
        raw = _clean_json(_extract_text(response.content))
        duplicates = json.loads(raw)
    except Exception as exc:
        logger.warning("Duplicate detection LLM call failed (%s) — skipping", exc)
        return products

    if not isinstance(duplicates, list):
        return products

    # Remove the more expensive listing for each duplicate pair
    remove_ids: set[str] = set()
    for dup in duplicates:
        di = dup.get("daraz_index", -1)
        ai = dup.get("amazon_index", -1)
        if 0 <= di < len(daraz) and 0 <= ai < len(amazon):
            d_prod = daraz[di]
            a_prod = amazon[ai]
            try:
                d_price = float(d_prod.get("price_display", 0) or 0)
            except (TypeError, ValueError):
                d_price = 0.0
            try:
                a_price = float(a_prod.get("price_display", 0) or 0)
            except (TypeError, ValueError):
                a_price = 0.0

            if d_price <= a_price:
                remove_ids.add(a_prod["id"])
                kept, removed = d_prod, a_prod
            else:
                remove_ids.add(d_prod["id"])
                kept, removed = a_prod, d_prod

            removed["filter_status"] = "excluded"
            removed["filter_reason"] = (
                f"Duplicate of {kept['name']} on {kept['source']} "
                f"({kept['price_display']:.0f} {kept['currency_display']} is cheaper)"
            )
            removed["filter_name"] = "duplicate"
            log.append({
                "product_name": removed["name"], "product_source": removed["source"],
                "filter_name": "duplicate", "decision": "fail",
                "reason": removed["filter_reason"],
                "threshold": "cheapest listing",
                "actual_value": f"{removed['price_display']:.0f} {removed['currency_display']}",
            })
            kept["cross_platform_note"] = (
                f"Also on {removed['source']} for "
                f"{removed['price_display']:.0f} {removed['currency_display']}"
            )

    return [p for p in products if p["id"] not in remove_ids]


# ---------------------------------------------------------------------------
# Graph node function
# ---------------------------------------------------------------------------
async def filter_node(state: ShoppingState) -> dict:
    """
    LangGraph node: runs the 5-stage progressive filter pipeline.
    Every decision is logged for Layer 1 explainability.
    """
    all_products = list(state.get("all_products", []))
    budget_max = state.get("budget_max")
    budget_currency = state.get("budget_currency", "PKR")
    display_currency = state.get("display_currency", "PKR")
    min_reviews = state.get("min_reviews", settings.DEFAULT_MIN_REVIEWS)
    try:
        min_reviews = int(min_reviews) if min_reviews is not None else settings.DEFAULT_MIN_REVIEWS
    except (TypeError, ValueError):
        min_reviews = settings.DEFAULT_MIN_REVIEWS
    search_terms = state.get("search_terms", [])
    model_name = state.get("model", "gemini-3-flash-preview")
    active_llm = _get_llm(model_name)
    errors: list[str] = list(state.get("errors", []))

    total_fetched = len(all_products)
    daraz_count = sum(1 for p in all_products if p["source"] == "daraz")
    amazon_count = sum(1 for p in all_products if p["source"] == "amazon")
    filter_log: list[dict] = []
    all_excluded: list[dict] = []

    def _collect_excluded(before: list[dict], after: list[dict]) -> None:
        after_ids = {p["id"] for p in after}
        for p in before:
            if p["id"] not in after_ids and p.get("filter_status") == "excluded":
                all_excluded.append(p)

    # --- Stage 1: Relevance & Brand (LLM) — runs FIRST so brand/type filtering
    #              happens before any products are dropped by price or review count.
    #              This prevents expensive brand-specific products from being removed
    #              by budget before the LLM can identify them as the correct brand. ---
    before = list(all_products)
    try:
        products = await _relevance_filter(all_products, search_terms, filter_log, active_llm)
    except Exception as exc:
        logger.error("Relevance filter failed: %s", exc)
        errors.append(f"Relevance filter error: {exc}")
        products = list(all_products)
    _collect_excluded(before, products)
    after_relevance = len(products)

    # --- Stage 2: Budget (with 10% margin) ---
    before = list(products)
    products = _budget_filter(products, budget_max, budget_currency, display_currency, filter_log)
    _collect_excluded(before, products)
    after_budget = len(products)

    # --- Stage 3: Minimum reviews (only when no budget is defined) ---
    if budget_max is None:
        before = list(products)
        products = _review_filter(products, min_reviews, filter_log)
        _collect_excluded(before, products)
    after_reviews = len(products)

    # --- Stage 4: Duplicate detection (LLM) — called ONCE ---
    before = list(products)
    try:
        products = await _duplicate_filter(products, filter_log, active_llm)
    except Exception as exc:
        logger.error("Duplicate filter failed: %s", exc)
        errors.append(f"Duplicate filter error: {exc}")
    _collect_excluded(before, products)
    after_duplicates = len(products)

    # --- Build funnel stats ---
    funnel_stats = {
        "total_fetched": total_fetched,
        "daraz_count": daraz_count,
        "amazon_count": amazon_count,
        "after_relevance_filter": after_relevance,
        "after_budget_filter": after_budget,
        "after_review_filter": after_reviews,
        "after_duplicate_filter": after_duplicates,
        "total_removed": total_fetched - after_duplicates,
        "removal_breakdown": {
            "relevance": total_fetched - after_relevance,
            "budget": after_relevance - after_budget,
            "minimum_reviews": after_budget - after_reviews if budget_max is None else 0,
            "duplicate": after_reviews - after_duplicates,
        },
    }

    logger.info(
        "Filter pipeline complete: %d → %d products (removed %d)",
        total_fetched, after_duplicates, total_fetched - after_duplicates,
    )

    # --- Persist filter decisions to Supabase ---
    # The scraper saves all products with filter_status="included" by default.
    # We must update excluded products in the DB so switch-currency and follow-up
    # endpoints can correctly distinguish included vs. excluded rows.
    session_id = state.get("session_id", "")
    if session_id and all_excluded:
        try:
            from database.models import Product
            from sqlalchemy import select
            async with async_session_maker() as db:
                result_db = await db.execute(
                    select(Product).where(Product.session_id == session_id)
                )
                db_map = {str(p.id): p for p in result_db.scalars().all()}
                for p in all_excluded:
                    pid = p.get("id", "")
                    if pid in db_map:
                        db_map[pid].filter_status = "excluded"
                        db_map[pid].filter_reason = p.get("filter_reason")
                        db_map[pid].filter_name = p.get("filter_name")
                await db.commit()
            logger.info("Persisted %d excluded products to Supabase", len(all_excluded))
        except Exception as exc:
            logger.error("Failed to persist filter decisions to Supabase: %s", exc)
            errors.append(f"DB filter persistence failed: {exc}")

    return {
        "filtered_products": products,
        "excluded_products": all_excluded,
        "filter_log": filter_log,
        "funnel_stats": funnel_stats,
        "current_step": "filter_done",
        "errors": errors,
    }
