"""
generate_workflow_diagram.py

Visualizes the ShopExplain AI LangGraph state graph as:
  1. Mermaid diagram  (always works — paste at mermaid.live)
  2. PNG image        (via mermaid.ink API, then pygraphviz fallback)
  3. ASCII art        (requires grandalf: pip install grandalf)

Install requirements:
    pip install langgraph langchain-core grandalf
"""

import os
from typing import Annotated, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


# ---------------------------------------------------------------------------
# State (mirrors backend/graph/state.py)
# ---------------------------------------------------------------------------
class ShoppingState(dict):
    pass


# ---------------------------------------------------------------------------
# Stub nodes — topology only, no real logic
# ---------------------------------------------------------------------------
def supervisor_node(state):          return {"current_step": "supervisor"}
def keyword_confirmation_node(state): return {"current_step": "keyword_confirmation"}
def scraper_node(state):             return {"current_step": "scraper"}
def filter_node(state):              return {"current_step": "filter"}
def analyzer_node(state):            return {"current_step": "analyzer"}
def reviewer_node(state):            return {"current_step": "reviewer"}
def explainer_node(state):           return {"current_step": "explainer"}
def currency_converter_node(state):  return {"current_step": "currency_converter"}


# ---------------------------------------------------------------------------
# Routing functions (conditional edges)
# ---------------------------------------------------------------------------
def route_after_confirmation(state) -> Literal["scraper", "__end__"]:
    return "scraper" if state.get("human_approved", False) else "__end__"


def route_after_explainer(state) -> Literal["supervisor", "currency_converter", "__end__"]:
    action = state.get("next_action")
    if action == "follow_up":        return "supervisor"
    if action == "switch_currency":  return "currency_converter"
    return "__end__"


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------
def build_graph() -> StateGraph:
    graph = StateGraph(ShoppingState)

    graph.add_node("Supervisor",           supervisor_node)
    graph.add_node("User Confirmation", keyword_confirmation_node)
    graph.add_node("Scraper",              scraper_node)
    graph.add_node("Filter",               filter_node)
    graph.add_node("Analyzer",             analyzer_node)
    graph.add_node("Reviewer",             reviewer_node)
    graph.add_node("Explainer",            explainer_node)
    graph.add_node("Currency Converter",   currency_converter_node)

    graph.add_edge(START, "Supervisor")
    graph.add_edge("Supervisor", "User Confirmation")

    graph.add_conditional_edges(
        "User Confirmation",
        route_after_confirmation,
        {"scraper": "Scraper", "__end__": END},
    )

    graph.add_edge("Scraper",   "Filter")
    graph.add_edge("Filter",    "Analyzer")
    graph.add_edge("Analyzer",  "Reviewer")
    graph.add_edge("Reviewer",  "Explainer")

    graph.add_conditional_edges(
        "Explainer",
        route_after_explainer,
        {
            "supervisor":         "Supervisor",
            "currency_converter": "Currency Converter",
            "__end__":            END,
        },
    )

    graph.add_edge("Currency Converter", END)

    return graph


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------
def visualize(graph: StateGraph, output_dir: str = ".") -> None:
    compiled = graph.compile()
    drawable = compiled.get_graph()

    os.makedirs(output_dir, exist_ok=True)

    # ── Method 1: Mermaid text (always works) ──────────────────────────────
    print("\n" + "=" * 60)
    print("  MERMAID DIAGRAM")
    print("  Paste at: https://mermaid.live")
    print("=" * 60 + "\n")

    mermaid_code = drawable.draw_mermaid()
    print(mermaid_code)

    mmd_path = os.path.join(output_dir, "workflow_diagram.mmd")
    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid_code)
    print(f"  Saved -> {os.path.abspath(mmd_path)}")

    # ── Method 2a: PNG via mermaid.ink API ─────────────────────────────────
    png_path = os.path.join(output_dir, "workflow_diagram.png")
    try:
        png_bytes = drawable.draw_mermaid_png()
        with open(png_path, "wb") as f:
            f.write(png_bytes)
        print(f"  PNG  -> {os.path.abspath(png_path)}  (mermaid.ink API)")
        return
    except Exception as e:
        print(f"  mermaid.ink failed ({e}), trying pygraphviz...")

    # ── Method 2b: PNG via pygraphviz ──────────────────────────────────────
    try:
        png_bytes = drawable.draw_png()
        with open(png_path, "wb") as f:
            f.write(png_bytes)
        print(f"  PNG  -> {os.path.abspath(png_path)}  (pygraphviz)")
        return
    except Exception as e:
        print(f"  pygraphviz failed ({e}), falling back to ASCII...")

    # ── Method 3: ASCII art (grandalf) ─────────────────────────────────────
    try:
        ascii_art = drawable.draw_ascii()
        print("\n" + "=" * 60)
        print("  ASCII GRAPH")
        print("=" * 60 + "\n")
        print(ascii_art)

        txt_path = os.path.join(output_dir, "workflow_diagram.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(ascii_art)
        print(f"  Saved -> {os.path.abspath(txt_path)}")
    except Exception as e:
        print(f"  ASCII fallback failed: {e}")
        print("  Install grandalf for ASCII art: pip install grandalf")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\nBuilding ShopExplain AI state graph...\n")
    graph = build_graph()

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph_output")
    visualize(graph, output_dir)

    print("\n" + "=" * 60)
    print(f"  Done. Output files in: {output_dir}/")
    print("=" * 60 + "\n")
