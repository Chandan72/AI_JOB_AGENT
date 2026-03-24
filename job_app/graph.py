from langgraph.graph import StateGraph, END, START
from job_app.state import AgentState
from job_app.nodes import (
    router,
    job_fetcher,
    job_extractor,
    company_researcher,
    ats_expert,
    cover_letter_generator,
    email_intent_selector,
    cold_email_drafter,
    human_feedback_loop,
    gmail_sender,
    
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
    
    return "job_extractor"


def build_graph():
    graph = StateGraph(AgentState)

    # ── Register all nodes ─────────────────────────────────────
    graph.add_node("router", router)
    
    graph.add_node("job_extractor", job_extractor)
    graph.add_node("company_researcher", company_researcher)
    graph.add_node("ats_expert", ats_expert)
    graph.add_node("cover_letter_generator", cover_letter_generator)
    graph.add_node("email_intent_selector", email_intent_selector)
    
    graph.add_node("cold_email_drafter", cold_email_drafter)
    graph.add_node("human_feedback_loop", human_feedback_loop)
    graph.add_node("gmail_sender", gmail_sender)
    
    graph.add_node("output_formatter", output_formatter)

    # ── Entry point ────────────────────────────────────────────
    graph.add_edge(START, "router")

    # ── Conditional branch after router ───────────────────────
    graph.add_conditional_edges(
        "router",
        _route_after_router,
        {
            
            "job_extractor": "job_extractor",
            "output_formatter": "output_formatter",
        },
    )

    # ── job_fetcher always goes to job_extractor ───────────────
    
    graph.add_edge("job_extractor", "company_researcher")

    # ── Linear pipeline after extraction ──────────────────────
    graph.add_edge("company_researcher", "ats_expert")
    graph.add_edge("ats_expert", "cover_letter_generator")
    graph.add_edge("cover_letter_generator", "email_intent_selector")
    graph.add_edge("email_intent_selector", "cold_email_drafter")
    graph.add_edge("cold_email_drafter", "human_feedback_loop")
    graph.add_edge("human_feedback_loop", "gmail_sender")
    graph.add_edge("gmail_sender", "output_formatter")
    

    # ── End ────────────────────────────────────────────────────
    graph.add_edge("output_formatter", END)

    return graph.compile()


# Compiled once — reused across all runs
job_application_graph = build_graph()