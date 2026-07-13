"""
services/input_gate.py — LLM-based safety and validity gate for user input.

This module blocks harmful, injection-like, or non-shopping prompts before
they are passed into the agent graph.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


REFUSAL_MESSAGE = (
    "I can't help with running commands or installing packages. "
    "I can help you find products. Try: 'wireless keyboard under $50'."
)

# High-confidence, command-like patterns and prompt-injection strings.
THREAT_PATTERNS = [
    r"\b(pip|pip3)\s+install\b",
    r"\b(npm|yarn|pnpm)\s+install\b",
    r"\b(apt-get|apt|brew|choco|winget)\s+install\b",
    r"\brm\s+-rf\b",
    r"\b(del|erase)\s+/[fqs]\b",
    r"\b(curl|wget)\b[^\n]*\|\s*(bash|sh)\b",
    r"\b(powershell|cmd\.exe|bash|sh)\b\s+-c\b",
    r"\b(ignore|override)\s+(all\s+)?(previous|above)\s+instructions\b",
    r"\b(reveal|show|print)\s+(the\s+)?(system|hidden)\s+prompt\b",
    r"\bsystem\s+prompt\b",
]

COMMAND_TOKENS = [
    "pip",
    "pip3",
    "npm",
    "npx",
    "yarn",
    "pnpm",
    "sudo",
    "rm",
    "del",
    "curl",
    "wget",
    "bash",
    "sh",
    "powershell",
    "cmd",
    "python",
    "node",
    "git",
    "apt",
    "apt-get",
    "brew",
    "choco",
    "winget",
]

WORD_PRODUCT_KEYWORDS = [
    "shoe",
    "shoes",
    "sneaker",
    "sneakers",
    "boot",
    "boots",
    "sandal",
    "sandals",
    "backpack",
    "bag",
    "laptop",
    "notebook",
    "phone",
    "smartphone",
    "tablet",
    "monitor",
    "keyboard",
    "mouse",
    "headphones",
    "earbuds",
    "earphones",
    "camera",
    "lens",
    "tripod",
    "charger",
    "cable",
    "router",
    "printer",
    "chair",
    "desk",
    "table",
    "sofa",
    "mattress",
    "pillow",
    "fan",
    "heater",
    "microwave",
    "oven",
    "blender",
    "juicer",
    "mixer",
    "toaster",
    "kettle",
    "iron",
    "vacuum",
    "fridge",
    "refrigerator",
    "tv",
    "television",
    "speaker",
    "watch",
    "smartwatch",
    "shirt",
    "t-shirt",
    "jeans",
    "jacket",
    "hoodie",
    "dress",
    "skirt",
    "perfume",
    "lotion",
    "shampoo",
    "soap",
    "toothbrush",
    "toothpaste",
    "bottle",
    "dumbbell",
    "treadmill",
    "bike",
    "bicycle",
    "helmet",
    "gloves",
    "console",
    "ssd",
    "hdd",
    "ram",
    "gpu",
    "cpu",
    "microphone",
    "mic",
    "webcam",
]

PHRASE_PRODUCT_KEYWORDS = [
    "power bank",
    "graphics card",
    "air conditioner",
    "ring light",
    "water bottle",
    "laptop stand",
    "gaming chair",
]

WORD_PRODUCT_RE = re.compile(r"\b(?:" + "|".join(map(re.escape, WORD_PRODUCT_KEYWORDS)) + r")\b")
COMMAND_TOKEN_RE = re.compile(r"\b(?:" + "|".join(map(re.escape, COMMAND_TOKENS)) + r")\b")
SHOPPING_HINT_RE = re.compile(
    r"\b(buy|price|prices|deal|deals|discount|sale|best|top|cheap|affordable|budget|under|below|compare|vs|versus)\b"
)
PRICE_RE = re.compile(
    r"(\$|rs\.?|pkr|usd|inr|eur|gbp)\s*\d+|\d+\s*(usd|pkr|rs\.?|inr|eur|gbp)|\b(under|below|less than|upto|up to)\s*\d+"
)
SIZE_RE = re.compile(r"\b\d+(?:\.\d+)?\s?(inch|in|cm|mm|gb|tb|mah|ml|l|kg|g)\b")


def _normalize_input(text: str) -> str:
    r"""Normalize input to prevent subtle attacks (e.g. s\y\s\t\e\m)."""
    # Strip backslashes, unless they are used for something standard, but since it's a shopping bot,
    # stripping all backslashes is an effective way to stop obfuscation like s\y\s\t\e\m.
    text = text.replace("\\", "")
    # Collapse multiple whitespace characters (including newlines) into a single space
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _has_high_confidence_threat(query: str) -> tuple[bool, str]:
    q = _normalize_input(query)
    for pattern in THREAT_PATTERNS:
        if re.search(pattern, q):
            return True, "command_or_injection"

    # Check for semicolon or other command chaining operators combined with known command tokens.
    if re.search(r"(&&|\|\||;|\||>)", q) and COMMAND_TOKEN_RE.search(q):
        return True, "command_operator"

    return False, ""


def _looks_like_shopping(query: str) -> bool:
    q = _normalize_input(query)
    score = 0
    if WORD_PRODUCT_RE.search(q) or any(phrase in q for phrase in PHRASE_PRODUCT_KEYWORDS):
        score += 2
    if PRICE_RE.search(q):
        score += 2
    if SIZE_RE.search(q):
        score += 1
    if SHOPPING_HINT_RE.search(q):
        score += 1
    return score >= 2


async def evaluate_input_gate(
    user_query: str,
    model_name: str = "gemini-3-flash-preview",
    *,
    is_followup: bool = False,
) -> dict:
    """
    Evaluate whether a user query is safe.
    Now uses purely deterministic logic without LLM fallback.
    """
    query = (user_query or "").strip()
    if not query:
        return {"allowed": True, "reason": "empty_query", "message": "", "confidence": 1.0}

    threat_hit, threat_reason = _has_high_confidence_threat(query)
    if threat_hit:
        logger.info("Input gate blocked query. reason=%s query=%s", threat_reason, user_query)
        return {
            "allowed": False,
            "reason": threat_reason,
            "message": REFUSAL_MESSAGE,
            "confidence": 1.0,
        }

    if _looks_like_shopping(query):
        return {
            "allowed": True,
            "reason": "shopping_heuristic",
            "message": "",
            "confidence": 1.0,
        }

    # If it's not a clear threat and not clearly shopping, it's ambiguous.
    # Based on the new design, we allow ambiguous off-topic queries.
    return {
        "allowed": True,
        "reason": "ambiguous_query",
        "message": "",
        "confidence": 1.0,
    }

