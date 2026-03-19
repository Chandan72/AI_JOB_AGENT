from langgraph.graph import StateGraph, END, START
from src.state import AgentState
from src.nodes import (
    router,
    job_fetcher,
    job_extractor,
    company_researcher,
    resume_generator,
    cover_letter_generator,
    cold_email_drafter,
    pdf_resume_generator,
    output_formatter,
)


def _route_after_router(state: AgentState) -> str:
    """
    After router runs, decide next node:
    - URL input  → job_fetcher (scrape the page)
    - Text input → job_extractor (skip scraping)
    - Any error  → output_formatter (show error)
    """
    if state.get("error"):
        return "output_formatter"
    if state.get("input_type") == "url":
        return "job_fetcher"
    return "job_extractor"


def build_graph():
    graph = StateGraph(AgentState)

    # ── Register all nodes ─────────────────────────────────────
    graph.add_node("router", router)
    graph.add_node("job_fetcher", job_fetcher)
    graph.add_node("job_extractor", job_extractor)
    graph.add_node("company_researcher", company_researcher)
    graph.add_node("resume_generator", resume_generator)
    graph.add_node("cover_letter_generator", cover_letter_generator)
    graph.add_node("cold_email_drafter", cold_email_drafter)
    graph.add_node("pdf_resume_generator", pdf_resume_generator)
    graph.add_node("output_formatter", output_formatter)

    # ── Entry point ────────────────────────────────────────────
    graph.add_edge(START, "router")

    # ── Conditional branch after router ───────────────────────
    graph.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "job_fetcher": "job_fetcher",
            "job_extractor": "job_extractor",
            "output_formatter": "output_formatter",
        },
    )

    # ── job_fetcher always goes to job_extractor ───────────────
    graph.add_edge("job_fetcher", "job_extractor")
    graph.add_edge("job_extractor", "company_researcher")

    # ── Linear pipeline after extraction ──────────────────────
    graph.add_edge("company_researcher", "resume_generator")
    graph.add_edge("resume_generator", "cover_letter_generator")
    graph.add_edge("cover_letter_generator", "cold_email_drafter")
    graph.add_edge("cold_email_drafter", "pdf_resume_generator")
    graph.add_edge("pdf_resume_generator", "output_formatter")

    # ── End ────────────────────────────────────────────────────
    graph.add_edge("output_formatter", END)

    return graph.compile()


# Compiled once — reused across all runs
job_application_graph = build_graph()