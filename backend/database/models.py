"""
database/models.py — SQLAlchemy ORM models for Supabase PostgreSQL.

Tables:
  - search_sessions  : persisted search queries with funnel stats & explanations
  - products         : every product (included or excluded) linked to a session
  - exchange_rate_cache : cached USD→PKR rates to stay under API limits
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .connection import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# SearchSession — one row per user search
# ---------------------------------------------------------------------------
class SearchSession(Base):
    __tablename__ = "search_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String, nullable=False)
    display_currency = Column(String, nullable=False, default="PKR")
    search_terms = Column(JSON, default=list)           # list[str]
    budget_max = Column(Float, nullable=True)
    exchange_rate_used = Column(Float, nullable=False, default=0.0)
    funnel_stats = Column(JSON, default=dict)            # full funnel stats dict
    fetch_explanation = Column(Text, default="")
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationship
    products = relationship("Product", back_populates="session", lazy="selectin")

    def __repr__(self) -> str:
        return f"<SearchSession {self.id} q='{self.query}'>"


# ---------------------------------------------------------------------------
# Product — every product tied to a search session
# ---------------------------------------------------------------------------
class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("search_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source = Column(String, nullable=False)                # "daraz" or "amazon"
    name = Column(String, nullable=False)
    price_original = Column(Float, nullable=False)
    currency_original = Column(String, nullable=False)     # "PKR" or "USD" or "AED"
    price_display = Column(Float, nullable=False)
    currency_display = Column(String, nullable=False)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    product_url = Column(Text, default="")
    image_url = Column(Text, default="")
    discount_percentage = Column(Float, nullable=True)
    brand = Column(String, nullable=True)
    value_score = Column(Float, nullable=True)
    recommendation_badge = Column(String, nullable=True)
    reasoning_chain = Column(JSON, nullable=True)          # list[str]
    cross_platform_note = Column(String, nullable=True)

    # Filter audit trail
    filter_status = Column(String, default="included")     # "included" or "excluded"
    filter_reason = Column(String, nullable=True)
    filter_name = Column(String, nullable=True)

    # Review analysis (populated by review extractor agent)
    review_sentiment = Column(Float, nullable=True)
    review_positive_themes = Column(JSON, nullable=True)   # list[str]
    review_negative_themes = Column(JSON, nullable=True)   # list[str]
    review_summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # Relationship
    session = relationship("SearchSession", back_populates="products")

    def __repr__(self) -> str:
        return f"<Product {self.source}:{self.name[:30]}>"


# ---------------------------------------------------------------------------
# ExchangeRateCache — persisted rate cache (Tier 2)
# ---------------------------------------------------------------------------
class ExchangeRateCache(Base):
    __tablename__ = "exchange_rate_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    base_currency = Column(String, nullable=False)         # e.g. "USD"
    target_currency = Column(String, nullable=False)       # e.g. "PKR"
    rate = Column(Float, nullable=False)
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    source = Column(String, nullable=False)                # "exchangerate-api" or "fallback"

    def __repr__(self) -> str:
        return f"<ExchangeRateCache {self.base_currency}→{self.target_currency} = {self.rate}>"
