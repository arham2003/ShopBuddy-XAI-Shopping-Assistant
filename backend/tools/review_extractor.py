"""
tools/review_extractor.py — Utility for extracting and summarising review text.

Pulls review data from the raw scraper output (both Daraz and Amazon) and
structures it into a format the review-analysis agent can consume.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_reviews_from_product(product: dict) -> list[dict]:
    """
    Pull review text from a raw scraped product dict.

    Amazon products may have `top_reviews` (list of CustomerReview dicts).
    Daraz products embed review snippets inside the description object.
    Returns a flat list of {"text": str, "rating": float | None}.
    """
    reviews: list[dict] = []

    # --- Amazon-style top_reviews ---
    for review in product.get("top_reviews", []):
        text = ""
        if isinstance(review, dict):
            text = review.get("text", "") or review.get("body", "")
            rating = review.get("rating")
        else:
            text = str(review)
            rating = None

        if text.strip():
            reviews.append({"text": text.strip(), "rating": rating})

    # --- Daraz-style embedded reviews (inside description) ---
    desc = product.get("description")
    if isinstance(desc, dict):
        highlights = desc.get("highlights", [])
        if highlights and isinstance(highlights, list):
            # Highlights can serve as pseudo-review snippets
            for h in highlights:
                if isinstance(h, str) and h.strip():
                    reviews.append({"text": h.strip(), "rating": None})

    return reviews


def aggregate_review_text(products: list[dict]) -> dict[str, str]:
    """
    Build a product_id → combined_review_text mapping.
    Used by the review-analysis agent to run sentiment analysis in batch.
    """
    mapping: dict[str, str] = {}
    for product in products:
        pid = product.get("id", "")
        reviews = extract_reviews_from_product(product)
        if reviews:
            combined = "\n---\n".join(r["text"] for r in reviews)
            mapping[pid] = combined
    return mapping


def compute_basic_sentiment(text: str) -> float:
    """
    Dead-simple keyword-based sentiment score (0.0–1.0) for when the LLM
    is unavailable or for quick pre-filtering.

    NOT a replacement for the LLM-powered review analysis — this is a
    lightweight fallback only.
    """
    positive_words = {
        "great", "excellent", "love", "amazing", "perfect", "best",
        "good", "awesome", "fantastic", "wonderful", "happy", "recommend",
        "quality", "solid", "works", "fast", "easy", "nice", "durable",
    }
    negative_words = {
        "bad", "terrible", "worst", "broken", "cheap", "waste", "poor",
        "awful", "horrible", "defective", "useless", "disappointed",
        "slow", "weak", "flimsy", "fake", "scam", "return", "refund",
    }

    words = set(text.lower().split())
    pos = len(words & positive_words)
    neg = len(words & negative_words)
    total = pos + neg

    if total == 0:
        return 0.5  # neutral

    return round(pos / total, 2)
