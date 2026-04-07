"""
agents/supervisor.py — Entry-point agent that parses user intent.

Uses a ReAct loop (create_react_agent) with two tools:
  1. parse_query_tool  — extracts search terms, budget, filters from the query
  2. validate_keywords_tool — LLM self-check on extracted terms

Also creates a new SearchSession in Supabase and trims conversation history
to keep context lean.

BUG FIX: ChatGoogleGenerativeAI returns response.content as a list of parts
(not a plain string) for Gemini 3 models. _extract_text() handles both cases.
"""

from __future__ import annotations

import json
import logging
import re
import uuid

from langchain_core.messages import HumanMessage, AIMessage, trim_messages
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from config import settings
from database.connection import async_session_maker
from database import crud
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
    return llm  # default: gemini-3-flash-preview


# ---------------------------------------------------------------------------
# Helper: safely extract a plain string from any LangChain message content
# ---------------------------------------------------------------------------
def _extract_text(content) -> str:
    """
    ChatGoogleGenerativeAI may return .content as either:
      - str  (single text response)
      - list (multimodal parts: [{"type": "text", "text": "..."}, ...])
    This function handles both and always returns a plain string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                # {"type": "text", "text": "..."} or {"text": "..."}
                parts.append(part.get("text", ""))
        return "".join(parts)
    return str(content)


def _clean_json(text: str) -> str:
    """Strip markdown code fences from LLM JSON responses."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (e.g. ```json\n)
        text = re.sub(r'^```[a-z]*\n?', '', text)
        # Remove closing fence
        text = re.sub(r'\n?```$', '', text)
    return text.strip()


def _coerce_min_reviews(value) -> int:
    """Normalize min_reviews to a safe positive integer fallback."""
    try:
        if value is None:
            return settings.DEFAULT_MIN_REVIEWS
        iv = int(value)
        return iv if iv >= 0 else settings.DEFAULT_MIN_REVIEWS
    except (TypeError, ValueError):
        return settings.DEFAULT_MIN_REVIEWS


# ---------------------------------------------------------------------------
# Parse prompt (shared across all models)
# ---------------------------------------------------------------------------
_PARSE_PROMPT = """You are a PRODUCT TERM EXTRACTOR for e-commerce search.

Your ONLY job is to convert the user's message into 1 to 3 PRODUCT NAMES that can be used as shopping search terms on Amazon or Daraz.

Hard rules:
- Output only product names or product-type phrases.
- Do NOT output budget words, prices, numbers related to price, or currency.
- Do NOT output helping verbs, filler words, action words, or sentence fragments.
- Do NOT output phrases like: buy, want, need, looking for, best, good, cheap, under, around, budget, please, recommend, show me.
- Do NOT invent exact specs, brands, model numbers, or sizes unless the user explicitly states them.
- Do NOT return search queries. Return product terms only.
- If the user is vague, choose the safest broad product category.
- If the user mentions a feature, include only the feature that is part of the product name in real shopping listings.
- Keep each term short, natural, and usable as a marketplace product title.
- Each term must be a real product noun phrase.

Examples:
User: "I want something for cleaning carpet automatically"
Output: ["robot vacuum cleaner"]

User: "noise cancelling headphones for flights"
Output: ["noise cancelling headphones", "ANC headphones"]

User: "portable thing to charge my phone"
Output: ["power bank"]

User: "machine that makes coffee from beans"
Output: ["espresso machine", "bean to cup coffee machine"]

User: "big screen tv"
Output: ["smart tv", "large screen tv"]

User: "gaming laptop under 100000 PKR"
Output: ["gaming laptop"]

User: "good camera phone budget 20000"
Output: ["camera phone"]

Return ONLY valid JSON in this exact format:
{{"search_terms": ["rephrased term 1", "rephrased term 2"], "budget_max": null, "budget_currency": "PKR", "min_reviews": 5, "category_hint": ""}}

Additional rules:
- product_terms must contain only nouns or noun phrases.
- Never include budget_max or price information in product_terms.
- Never include verbs, adjectives like good/best/cheap, or helper words.
- If no safe product term can be extracted, return an empty array.
"""


# ---------------------------------------------------------------------------
# Tool 1: Parse the user's shopping query
# ---------------------------------------------------------------------------
@tool
async def parse_query_tool(user_query: str) -> str:
    """
    Parse a shopping query into structured search parameters.
    Extracts: search_terms, budget_max, budget_currency, min_reviews, category_hint.
    Returns a JSON string with these fields.
    """
    prompt = _PARSE_PROMPT + f"\n\nUser query: \"{user_query}\""
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return _clean_json(_extract_text(response.content))


# ---------------------------------------------------------------------------
# Tool 2: Validate extracted keywords
# ---------------------------------------------------------------------------
@tool
async def validate_keywords_tool(search_terms: str, original_query: str) -> str:
    """
    Validate that extracted search terms accurately represent the user's intent.
    search_terms should be a JSON list string. original_query is the raw user query.
    Returns JSON with 'valid' (bool) and 'corrected_terms' (list) if needed.
    """
    prompt = f"""You extracted these search terms: {search_terms}
From this original query: "{original_query}"

Are these search terms accurate and sufficient for finding the right products?

Return ONLY valid JSON:
{{
  "valid": true,
  "corrected_terms": ["term1", "term2"],
  "reason": "why correction was needed (or 'looks good')"
}}
"""
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return _clean_json(_extract_text(response.content))


# ---------------------------------------------------------------------------
# Direct LLM parse (uses the selected model, not the ReAct wrapper)
# ---------------------------------------------------------------------------
async def _direct_parse(user_query: str, display_currency: str, active_llm=None) -> dict:
    """Call the LLM directly to parse the query into structured search params."""
    active_llm = active_llm or llm
    response = await active_llm.ainvoke([HumanMessage(content=_PARSE_PROMPT + f"\n\nUser query: \"{user_query}\"")])
    raw = _clean_json(_extract_text(response.content))
    data = json.loads(raw)
    return {
        "search_terms": data["search_terms"],
        "budget_max": data.get("budget_max"),
        "budget_currency": data.get("budget_currency", display_currency),
        "min_reviews": _coerce_min_reviews(data.get("min_reviews")),
        "category_hint": data.get("category_hint", ""),
    }


# ---------------------------------------------------------------------------
# ReAct agents — one per model (for manual testing flexibility)
# ---------------------------------------------------------------------------
_REACT_PROMPT = (
    "You are the Supervisor of a shopping assistant. Your job is to:\n"
    "1. Call parse_query_tool with the user's query to extract search parameters.\n"
    "2. Call validate_keywords_tool to verify the extracted terms are accurate.\n"
    "3. Return ONLY the final JSON object from parse_query_tool (with any corrections applied).\n"
    "Do not add any explanation. Return raw JSON only."
)

_supervisor_react = create_react_agent(
    model=llm,
    tools=[parse_query_tool, validate_keywords_tool],
    prompt=_REACT_PROMPT,
)

_supervisor_react_llama70b = create_react_agent(
    model=llm_llama70b,
    tools=[parse_query_tool, validate_keywords_tool],
    prompt=_REACT_PROMPT,
)

_supervisor_react_llama8b = create_react_agent(
    model=llm_llama8b,
    tools=[parse_query_tool, validate_keywords_tool],
    prompt=_REACT_PROMPT,
)


def _get_react_agent(model_name: str):
    """Return the ReAct agent for the requested model."""
    if model_name == "llama-3.3-70b-versatile":
        return _supervisor_react_llama70b
    if model_name == "llama-3.1-8b-instant":
        return _supervisor_react_llama8b
    return _supervisor_react


# ---------------------------------------------------------------------------
# Graph node function
# ---------------------------------------------------------------------------
async def supervisor_node(state: ShoppingState) -> dict:
    """
    LangGraph node: parses the user query, creates a DB session, and
    populates state with search constraints.
    """
    user_query = state["user_query"]
    display_currency = state.get("display_currency", "PKR")
    model_name = state.get("model", "gemini-3-flash-preview")
    errors: list[str] = list(state.get("errors", []))

    active_llm = _get_llm(model_name)
    react_agent = _get_react_agent(model_name)

    # Trim conversation history to last 6 messages (3 turns) to save tokens
    history = state.get("conversation_history", [])
    trim_messages(history, max_tokens=6, token_counter=len, strategy="last")

    # --- Strategy: try ReAct first, fall back to direct call ---
    parsed = None

    try:
        react_input = {"messages": [HumanMessage(content=user_query)]}
        # recursion_limit=10 allows ~4 tool-call rounds (Google AFC max_remote_calls equivalent)
        react_result = await react_agent.ainvoke(react_input, config={"recursion_limit": 10})

        # The last message in the ReAct chain contains the final answer
        final_content = react_result["messages"][-1].content
        final_text = _extract_text(final_content)

        # Try to parse JSON from the response
        cleaned = _clean_json(final_text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON object from mixed text
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            data = json.loads(json_match.group()) if json_match else {}

        if data and "search_terms" in data:
            parsed = {
                "search_terms": data.get("search_terms", [user_query]),
                "budget_max": data.get("budget_max"),
                "budget_currency": data.get("budget_currency", display_currency),
                "min_reviews": _coerce_min_reviews(data.get("min_reviews")),
                "category_hint": data.get("category_hint", ""),
            }

    except Exception as exc:
        logger.warning("Supervisor ReAct failed (%s) — trying direct parse", exc)

    # Fallback: call parse_query_tool directly (no ReAct wrapper)
    if parsed is None:
        try:
            parsed = await _direct_parse(user_query, display_currency, active_llm)
            logger.info("Supervisor used direct parse for: %s", user_query)
        except Exception as exc:
            logger.error("Direct parse also failed: %s", exc)
            errors.append(f"Query parsing failed: {exc}")
            parsed = {
                "search_terms": [user_query],
                "budget_max": None,
                "budget_currency": display_currency,
                "min_reviews": settings.DEFAULT_MIN_REVIEWS,
                "category_hint": "",
            }

    logger.info("Parsed query '%s' → terms=%s budget=%s", user_query, parsed["search_terms"], parsed["budget_max"])

    # --- Create search session in Supabase ---
    session_id = str(uuid.uuid4())
    try:
        async with async_session_maker() as db:
            await crud.create_search_session(db, {
                "id": uuid.UUID(session_id),
                "query": user_query,
                "display_currency": display_currency,
                "search_terms": parsed["search_terms"],
                "budget_max": parsed["budget_max"],
            })
        logger.info("Created search session %s for query: %s", session_id, user_query)
    except Exception as exc:
        logger.error("Failed to create search session in Supabase: %s", exc)
        errors.append(f"DB session creation failed: {exc}")

    return {
        "search_terms": parsed["search_terms"],
        "budget_max": parsed["budget_max"],
        "budget_currency": parsed["budget_currency"],
        "min_reviews": parsed["min_reviews"],
        "category_hint": parsed["category_hint"],
        "session_id": session_id,
        "current_step": "supervisor_done",
        "errors": errors,
        "conversation_history": [
            HumanMessage(content=user_query),
            AIMessage(content=f"Parsed search: {parsed['search_terms']}"),
        ],
    }
