"""
graph/state.py — Shared state schema for the LangGraph shopping workflow.

Every node reads from and writes to this TypedDict. Fields are grouped by
the pipeline stage that populates them.
"""

from __future__ import annotations

from typing import TypedDict, Annotated

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ShoppingState(TypedDict):
    # ── User input ──────────────────────────────────────────────────────
    user_query: str
    display_currency: str                              # "PKR" or "USD"
    model: str                                         # LLM model name
    conversation_history: Annotated[list[BaseMessage], add_messages]

    # ── Parsed constraints (set by Supervisor) ──────────────────────────
    search_terms: list[str]
    budget_max: float | None
    budget_currency: str
    min_reviews: int
    category_hint: str

    # ── Exchange rate (set by Scraper, used by all) ─────────────────────
    exchange_rate_usd_to_pkr: float
    exchange_rate_timestamp: str
    exchange_rate_source: str

    # ── Raw scrape results ──────────────────────────────────────────────
    daraz_products: list[dict]
    amazon_products: list[dict]
    all_products: list[dict]
    product_reviews: dict                   # {product_name_lower: [{"text": ..., "rating": ...}]}

    # ── Filter results ──────────────────────────────────────────────────
    filtered_products: list[dict]
    excluded_products: list[dict]
    filter_log: list[dict]
    funnel_stats: dict

    # ── Analysis results ────────────────────────────────────────────────
    ranked_products: list[dict]
    review_insights: dict

    # ── Explanations ────────────────────────────────────────────────────
    fetch_explanation: str
    recommendation_explanations: dict

    # ── Database ────────────────────────────────────────────────────────
    session_id: str                                    # UUID for this search session

    # ── Control flow ────────────────────────────────────────────────────
    current_step: str
    errors: list[str]
