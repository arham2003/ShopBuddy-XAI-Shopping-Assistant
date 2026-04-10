"""
models/schemas.py — Pydantic v2 schemas for request validation, response
serialization, and inter-agent data contracts.
"""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Unified product representation (used across all agents)
# ---------------------------------------------------------------------------
class UnifiedProduct(BaseModel):
    id: str                                     # UUID string
    source: str                                 # "daraz" or "amazon"
    name: str
    price_original: float                       # Raw price from source
    currency_original: str                      # "PKR", "USD", or "AED"
    price_display: float                        # Converted to user's display currency
    currency_display: str                       # User's chosen display currency
    rating: float
    review_count: int
    product_url: str
    image_url: str
    discount_percentage: float | None = None
    brand: str | None = None
    value_score: float | None = None
    recommendation_badge: str | None = None     # e.g. "Best Value", "Top Rated"
    reasoning_chain: list[str] | None = None    # step-by-step reasoning
    cross_platform_note: str | None = None      # comparison note across platforms
    filter_status: str = "included"             # "included" or "excluded"
    filter_reason: str | None = None            # why it was excluded
    filter_name: str | None = None              # which filter excluded it


# ---------------------------------------------------------------------------
# Explainability: filter audit trail
# ---------------------------------------------------------------------------
class FilterDecision(BaseModel):
    product_name: str
    product_source: str
    filter_name: str
    decision: str                               # "pass" or "fail"
    reason: str
    threshold: str
    actual_value: str


# ---------------------------------------------------------------------------
# Funnel statistics
# ---------------------------------------------------------------------------
class FunnelStats(BaseModel):
    total_fetched: int
    daraz_count: int
    amazon_count: int
    after_budget_filter: int
    after_review_filter: int
    after_trust_filter: int
    after_relevance_filter: int
    after_duplicate_filter: int
    total_removed: int
    removal_breakdown: dict


# ---------------------------------------------------------------------------
# Review analysis output
# ---------------------------------------------------------------------------
class ReviewInsight(BaseModel):
    product_id: str
    sentiment_score: float
    positive_themes: list[str]
    negative_themes: list[str]
    review_summary: str
    trust_score: float


# ---------------------------------------------------------------------------
# Recommendation explanation card (Layer 2 explainability)
# ---------------------------------------------------------------------------
class ExplanationCard(BaseModel):
    product_id: str
    recommendation_badge: str
    confidence_score: float
    reasoning_chain: list[str]
    trade_offs: str
    cross_platform_note: str | None = None


# ---------------------------------------------------------------------------
# Exchange rate info (returned to frontend)
# ---------------------------------------------------------------------------
class ExchangeRateInfo(BaseModel):
    usd_to_pkr: float
    pkr_to_usd: float
    last_updated: str
    source: str                                 # "exchangerate-api" or "fallback"


# ---------------------------------------------------------------------------
# API request schemas
# ---------------------------------------------------------------------------
class SearchRequest(BaseModel):
    query: str
    display_currency: str = "PKR"               # "PKR" or "USD"
    model: str = "gemini-3-flash-preview"       # LLM model to use
    thread_id: str | None = None                # set when resuming from interrupt
    approved: bool | None = None                # True/False to approve/reject interrupt


class QueryCancelRequest(BaseModel):
    thread_id: str


class FollowUpRequest(BaseModel):
    thread_id: str
    query: str
    display_currency: str = "PKR"
    model: str = "gemini-3-flash-preview"       # LLM model to use


class CurrencySwitchRequest(BaseModel):
    thread_id: str
    display_currency: str                       # "PKR" or "USD"


# ---------------------------------------------------------------------------
# Demo session listing
# ---------------------------------------------------------------------------
class DemoSession(BaseModel):
    session_id: str
    query: str
    display_currency: str
    product_count: int
    created_at: str
