"""
graph.py — Job Hunter LangGraph Pipeline
──────────────────────────────────────────
Assembles the 7-node daily job hunting pipeline.
"""

from langgraph.graph import StateGraph, END, START
from job_hunter.state import HunterState
from job_hunter.nodes import (
    profile_loader,
    job_scraper_node,
    deduplicator,
    keyword_filter,
    semantic_ranker,
    digest_generator_node,
    digest_email_sender,
)


def _check_error(state: HunterState) -> str:
    """Short-circuit to end if error detected."""
    if state.get("error"):
        return "end"
    return "continue"


def build_hunter_graph():
    graph = StateGraph(HunterState)

    # ── Register nodes ─────────────────────────────────────────
    graph.add_node("profile_loader",        profile_loader)
    graph.add_node("job_scraper",           job_scraper_node)
    graph.add_node("deduplicator",          deduplicator)
    graph.add_node("keyword_filter",        keyword_filter)
    graph.add_node("semantic_ranker",       semantic_ranker)
    graph.add_node("digest_generator",      digest_generator_node)
    graph.add_node("digest_email_sender",   digest_email_sender)

    # ── Linear pipeline ────────────────────────────────────────
    graph.add_edge(START,              "profile_loader")
    graph.add_edge("profile_loader",   "job_scraper")
    graph.add_edge("job_scraper",      "deduplicator")
    graph.add_edge("deduplicator",     "keyword_filter")
    graph.add_edge("keyword_filter",   "semantic_ranker")
    graph.add_edge("semantic_ranker",  "digest_generator")
    graph.add_edge("digest_generator", "digest_email_sender")
    graph.add_edge("digest_email_sender", END)

    return graph.compile()


job_hunter_graph = build_hunter_graph()