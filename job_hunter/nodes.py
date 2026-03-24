"""
nodes.py — Job Hunter LangGraph Nodes
───────────────────────────────────────
7 nodes that form the complete daily job hunting pipeline.
"""

from __future__ import annotations
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

from job_hunter.state import HunterState
from job_hunter.profile_parser import (
    parse_candidate_profile,
    extract_skill_keywords,
    generate_search_queries,
)
from job_hunter.job_scraper import scrape_jobs
from job_hunter.matcher import (
    keyword_prefilter,
    semantic_rank,
    generate_match_reasons,
)
from job_hunter.tracker import (
    filter_unseen_jobs,
    mark_jobs_as_seen,
    log_digest_run,
)
from job_hunter.digest_generator import (
    generate_html_digest,
    save_digest_to_file,
    send_digest_email,
)
from job_app.config import Config

console = Console()


# ── Node 1: Profile Loader ─────────────────────────────────────
def profile_loader(state: HunterState) -> HunterState:
    console.print(
        "\n[bold cyan]► Step 1/7:[/bold cyan] "
        "Loading candidate profile..."
    )

    if state.get("error"):
        return state

    try:
        profile = parse_candidate_profile(
            resume_path=state.get(
                "resume_pdf_path", "./candidate_data/resume.pdf"
            ),
            linkedin_path=state.get(
                "linkedin_pdf_path",
                "./candidate_data/linkedin.pdf"
            ),
        )

        keywords = extract_skill_keywords(profile)
        queries  = generate_search_queries(profile)

        console.print(
            f"   [green]✓ Profile loaded:[/green] "
            f"[bold]{profile.get('name', 'Candidate')}[/bold] — "
            f"{profile.get('current_title', '')}"
        )
        console.print(
            f"   Skills detected: "
            f"[dim]{', '.join(keywords[:8])}[/dim]"
        )

        return {
            **state,
            "candidate_profile": profile,
            "skill_keywords":    keywords,
            "search_queries":    queries,
            "current_step":      "profile_loader",
        }

    except Exception as e:
        return {
            **state,
            "error":        f"Profile loading failed: {str(e)}",
            "current_step": "profile_loader",
        }


# ── Node 2: Job Scraper ────────────────────────────────────────
def job_scraper_node(state: HunterState) -> HunterState:
    console.print(
        "\n[bold cyan]► Step 2/7:[/bold cyan] "
        "Searching job platforms..."
    )

    if state.get("error"):
        return state

    try:
        raw_jobs = scrape_jobs(
            search_queries=state.get("search_queries", []),
            max_results_per_query=5,
        )

        return {
            **state,
            "raw_jobs":     raw_jobs,
            "current_step": "job_scraper",
        }

    except Exception as e:
        return {
            **state,
            "error":        f"Job scraping failed: {str(e)}",
            "current_step": "job_scraper",
        }


# ── Node 3: Deduplicator ───────────────────────────────────────
def deduplicator(state: HunterState) -> HunterState:
    console.print(
        "\n[bold cyan]► Step 3/7:[/bold cyan] "
        "Filtering previously seen jobs..."
    )

    if state.get("error"):
        return state

    raw_jobs   = state.get("raw_jobs", [])
    fresh_jobs = filter_unseen_jobs(raw_jobs)

    if not fresh_jobs:
        return {
            **state,
            "error": (
                "No new jobs found today — all results were "
                "already seen in the last 7 days. "
                "Try again tomorrow."
            ),
            "current_step": "deduplicator",
        }

    return {
        **state,
        "fresh_jobs":   fresh_jobs,
        "current_step": "deduplicator",
    }


# ── Node 4: Keyword Filter ─────────────────────────────────────
def keyword_filter(state: HunterState) -> HunterState:
    console.print(
        "\n[bold cyan]► Step 4/7:[/bold cyan] "
        "Applying keyword pre-filter..."
    )

    if state.get("error"):
        return state

    filtered = keyword_prefilter(
        jobs=state.get("fresh_jobs", []),
        skill_keywords=state.get("skill_keywords", []),
        min_keyword_matches=1,
    )

    if not filtered:
        # Relax filter if nothing passes
        console.print(
            "   [yellow]⚠ No jobs passed keyword filter — "
            "relaxing threshold[/yellow]"
        )
        filtered = state.get("fresh_jobs", [])[:50]

    return {
        **state,
        "filtered_jobs": filtered,
        "current_step":  "keyword_filter",
    }


# ── Node 5: Semantic Ranker ────────────────────────────────────
def semantic_ranker(state: HunterState) -> HunterState:
    console.print(
        "\n[bold cyan]► Step 5/7:[/bold cyan] "
        "Semantic matching and ranking..."
    )

    if state.get("error"):
        return state

    try:
        ranked = semantic_rank(
            jobs=state.get("filtered_jobs", []),
            candidate_profile=state.get("candidate_profile", {}),
            top_n=20,
        )

        top_jobs = generate_match_reasons(
            jobs=ranked,
            candidate_profile=state.get("candidate_profile", {}),
        )

        # Save to tracker
        mark_jobs_as_seen(top_jobs)

        console.print(
            f"   [green]✓ Top {len(top_jobs)} jobs selected[/green]"
        )

        return {
            **state,
            "top_jobs":     top_jobs,
            "current_step": "semantic_ranker",
        }

    except Exception as e:
        return {
            **state,
            "error":        f"Semantic ranking failed: {str(e)}",
            "current_step": "semantic_ranker",
        }


# ── Node 6: Digest Generator ───────────────────────────────────
def digest_generator_node(state: HunterState) -> HunterState:
    console.print(
        "\n[bold cyan]► Step 6/7:[/bold cyan] "
        "Generating job digest..."
    )

    if state.get("error"):
        return state

    top_jobs    = state.get("top_jobs", [])
    profile     = state.get("candidate_profile", {})
    run_date    = datetime.now().strftime("%B %d, %Y")

    # Generate HTML digest
    html = generate_html_digest(
        jobs=top_jobs,
        candidate_name=profile.get("name", "Candidate"),
        run_date=run_date,
    )

    # Save to file
    file_path = save_digest_to_file(html)
    console.print(f"   [green]✓ Digest saved:[/green] [dim]{file_path}[/dim]")

    return {
        **state,
        "digest_html":  html,
        "digest_path":  file_path,
        "run_date":     run_date,
        "current_step": "digest_generator",
    }


# ── Node 7: Email Sender ───────────────────────────────────────
def digest_email_sender(state: HunterState) -> HunterState:
    console.print(
        "\n[bold cyan]► Step 7/7:[/bold cyan] "
        "Sending email digest..."
    )

    if state.get("error"):
        return state

    profile   = state.get("candidate_profile", {})
    recipient = profile.get("email", "")

    if not recipient:
        console.print(
            "   [yellow]⚠ No email found in profile — "
            "digest saved to file only[/yellow]"
        )
        return {
            **state,
            "email_sent":   False,
            "current_step": "digest_email_sender",
        }

    success, message = send_digest_email(
        html=state.get("digest_html", ""),
        recipient_email=recipient,
        candidate_name=profile.get("name", "Candidate"),
        job_count=len(state.get("top_jobs", [])),
    )

    # Log the run
    log_digest_run(
        jobs_found=len(state.get("raw_jobs", [])),
        jobs_sent=len(state.get("top_jobs", [])),
    )

    if success:
        console.print(
            f"   [bold green]✓ Digest sent to {recipient}[/bold green]"
        )
    else:
        console.print(f"   [yellow]⚠ Email failed: {message}[/yellow]")

    # Print summary
    _print_summary(state)

    return {
        **state,
        "email_sent":   success,
        "current_step": "complete",
    }


def _print_summary(state: HunterState) -> None:
    top_jobs = state.get("top_jobs", [])
    profile  = state.get("candidate_profile", {})

    top3 = "\n".join([
        f"  {i+1}. [bold]{j.get('title')}[/bold] "
        f"@ {j.get('company')} "
        f"[green]({int(j.get('match_score',0)*100)}% match)[/green]"
        for i, j in enumerate(top_jobs[:3])
    ])

    console.print(Panel(
        f"[bold green]✓ Daily Job Digest Complete![/bold green]\n\n"
        f"[bold]Candidate:[/bold] {profile.get('name', 'N/A')}\n"
        f"[bold]Jobs found:[/bold] {len(top_jobs)}\n"
        f"[bold]Digest saved:[/bold] {state.get('digest_path', '')}\n"
        f"[bold]Email sent:[/bold] "
        f"{'Yes' if state.get('email_sent') else 'No'}\n\n"
        f"[bold]Top 3 Matches:[/bold]\n{top3}",
        title="[bold]Job Hunter Agent[/bold]",
        border_style="green",
        padding=(1, 2),
    ))