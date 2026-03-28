"""
graph/workflow.py — Compiles the LangGraph StateGraph for the shopping assistant.

Flow:
  START → supervisor → keyword_confirmation (interrupt) → scraper → filter
        → analyzer → reviewer → explainer → END

The keyword_confirmation node uses LangGraph's interrupt() to pause and let
the user approve/reject extracted search terms before scraping begins.

Exports `shopping_graph` — the compiled, checkpointed graph ready for
astream() / ainvoke().
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from graph.state import ShoppingState
from agents.supervisor import supervisor_node
from agents.scraper import scraper_node
from agents.filter_agent import filter_node
from agents.analyzer import analyzer_node
from agents.reviewer import reviewer_node
from agents.explainer import explainer_node

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword confirmation node (uses interrupt for human-in-the-loop)
# ---------------------------------------------------------------------------
def keyword_confirmation_node(state: ShoppingState) -> dict | Command:
    """
    Pauses the graph via interrupt() so the frontend can display the parsed
    search terms and budget to the user for approval.

    Resume with:  Command(resume={"approved": True})   → continue to scraper
                  Command(resume={"approved": False})  → abort to END
    """
    search_terms = state.get("search_terms", [])
    budget_max = state.get("budget_max")
    budget_currency = state.get("budget_currency", "PKR")

    # This call suspends execution and sends data to the client
    user_decision = interrupt({
        "search_terms": search_terms,
        "budget_max": budget_max,
        "budget_currency": budget_currency,
        "message": "Please confirm these search parameters before we begin scraping.",
    })

    # When the graph resumes, user_decision contains the client's response
    approved = user_decision.get("approved", True) if isinstance(user_decision, dict) else True

    if not approved:
        return Command(goto=END)

    return {"current_step": "keywords_confirmed"}


# ---------------------------------------------------------------------------
# Router after explainer: follow-up vs. currency switch vs. done
# ---------------------------------------------------------------------------
def _after_explainer_router(state: ShoppingState) -> str:
    """
    Conditional edge after the explainer node.
    In a single-shot query this always goes to END.
    Follow-ups and currency switches are handled by separate API endpoints.
    """
    return END


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------
def build_shopping_graph() -> StateGraph:
    """Construct (but do not compile) the shopping StateGraph."""
    graph = StateGraph(ShoppingState)

    # Register nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("keyword_confirmation", keyword_confirmation_node)
    graph.add_node("scraper", scraper_node)
    graph.add_node("filter", filter_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("explainer", explainer_node)

    # Wire edges: linear pipeline with an interrupt gate
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "keyword_confirmation")
    graph.add_edge("keyword_confirmation", "scraper")
    graph.add_edge("scraper", "filter")
    graph.add_edge("filter", "analyzer")
    graph.add_edge("analyzer", "reviewer")
    graph.add_edge("reviewer", "explainer")
    graph.add_conditional_edges("explainer", _after_explainer_router)

    return graph


# ---------------------------------------------------------------------------
# Compiled graph singleton (with in-memory checkpointer for conversation memory)
# ---------------------------------------------------------------------------
memory = MemorySaver()
shopping_graph = build_shopping_graph().compile(checkpointer=memory)
