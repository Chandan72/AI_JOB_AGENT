from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from src.state import AgentState
from src.config import Config, get_llm
from src.tools import fetch_job_posting, detect_input_type
from src.prompts import (
    JOB_EXTRACTION_PROMPT,
    RESUME_GENERATION_PROMPT,
    COVER_LETTER_PROMPT,
    COLD_EMAIL_PROMPT,
)

console = Console()


# ── Helper Functions ───────────────────────────────────────────

def _format_profile(profile: dict) -> str:
    return json.dumps(profile, indent=2)


def _get_job_field(job_details: dict, field: str, default: str = "Not specified") -> str:
    value = job_details.get(field, default)
    if isinstance(value, list):
        return ", ".join(value) if value else default
    return str(value) if value else default


# ── Node 1: Router ─────────────────────────────────────────────

def router(state: AgentState) -> AgentState:
    console.print("\n[bold cyan]► Step 1/7:[/bold cyan] Routing input...")

    job_input = state.get("job_input", "").strip()
    if not job_input:
        return {
            **state,
            "error": "No job input provided. Pass a URL or paste a job description.",
            "current_step": "router",
        }

    input_type = detect_input_type(job_input)
    console.print(f"   Input type detected: [bold]{input_type.upper()}[/bold]")

    return {
        **state,
        "input_type": input_type,
        "raw_job_content": job_input if input_type == "text" else "",
        "current_step": "router",
    }


# ── Node 2: Job Fetcher ────────────────────────────────────────

def job_fetcher(state: AgentState) -> AgentState:
    console.print("\n[bold cyan]► Step 2/7:[/bold cyan] Fetching job posting from URL...")

    url = state.get("job_input", "")
    console.print(f"   URL: [dim]{url}[/dim]")

    content, error = fetch_job_posting(url)

    if error:
        console.print(f"   [yellow]⚠ Scraping failed: {error}[/yellow]")
        console.print("   [yellow]  Falling back to raw URL as context.[/yellow]")
        return {
            **state,
            "raw_job_content": f"Job URL: {url}\n\n[Note: Could not scrape — {error}]",
            "current_step": "job_fetcher",
        }

    word_count = len(content.split())
    console.print(f"   [green]✓ Extracted ~{word_count} words from page[/green]")

    return {
        **state,
        "raw_job_content": content,
        "current_step": "job_fetcher",
    }


# ── Node 3: Job Extractor ──────────────────────────────────────

def job_extractor(state: AgentState) -> AgentState:
    console.print("\n[bold cyan]► Step 3/7:[/bold cyan] Extracting structured job details...")

    if state.get("error"):
        return state

    raw_content = state.get("raw_job_content", "")
    if not raw_content:
        return {
            **state,
            "error": "No job content to extract from.",
            "current_step": "job_extractor"
        }

    llm = get_llm(temperature=0.0)
    chain = JOB_EXTRACTION_PROMPT | llm

    try:
        response = chain.invoke({"raw_job_content": raw_content})
        raw_json = response.content.strip()

        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]

        job_details = json.loads(raw_json)

        console.print(
            f"   [green]✓ Extracted:[/green] "
            f"[bold]{job_details.get('job_title', 'Unknown Role')}[/bold] "
            f"at [bold]{job_details.get('company_name', 'Unknown Company')}[/bold]"
        )

        return {
            **state,
            "job_details": job_details,
            "current_step": "job_extractor",
        }

    except json.JSONDecodeError as e:
        return {
            **state,
            "error": f"Failed to parse job details JSON: {str(e)}",
            "current_step": "job_extractor",
        }
    except Exception as e:
        return {
            **state,
            "error": f"Job extraction failed: {str(e)}",
            "current_step": "job_extractor",
        }


# ── Node 4: Resume Generator ───────────────────────────────────

def resume_generator(state: AgentState) -> AgentState:
    console.print("\n[bold cyan]► Step 4/7:[/bold cyan] Generating tailored resume...")

    if state.get("error"):
        return state

    job_details = state.get("job_details", {})
    user_profile = state.get("user_profile", {})

    if not user_profile:
        return {
            **state,
            "error": "User profile is empty. Load a profile JSON first.",
            "current_step": "resume_generator"
        }

    llm = get_llm(temperature=0.2)
    chain = RESUME_GENERATION_PROMPT | llm

    try:
        response = chain.invoke({
            "user_profile": _format_profile(user_profile),
            "company_name": _get_job_field(job_details, "company_name"),
            "job_title": _get_job_field(job_details, "job_title"),
            "required_skills": _get_job_field(job_details, "required_skills"),
            "preferred_skills": _get_job_field(job_details, "preferred_skills"),
            "responsibilities": _get_job_field(job_details, "responsibilities"),
            "requirements": _get_job_field(job_details, "requirements"),
            "tech_stack": _get_job_field(job_details, "tech_stack"),
            "seniority_level": _get_job_field(job_details, "seniority_level"),
        })

        resume_content = response.content.strip()
        console.print(f"   [green]✓ Resume generated[/green]")

        return {
            **state,
            "tailored_resume": resume_content,
            "current_step": "resume_generator",
        }

    except Exception as e:
        return {
            **state,
            "error": f"Resume generation failed: {str(e)}",
            "current_step": "resume_generator"
        }


# ── Node 5: Cover Letter Generator ────────────────────────────

def cover_letter_generator(state: AgentState) -> AgentState:
    console.print("\n[bold cyan]► Step 5/7:[/bold cyan] Writing cover letter...")

    if state.get("error"):
        return state

    job_details = state.get("job_details", {})
    user_profile = state.get("user_profile", {})

    llm = get_llm(temperature=0.5)
    chain = COVER_LETTER_PROMPT | llm

    try:
        response = chain.invoke({
            "user_profile": _format_profile(user_profile),
            "company_name": _get_job_field(job_details, "company_name"),
            "job_title": _get_job_field(job_details, "job_title"),
            "about_company": _get_job_field(job_details, "about_company"),
            "team_info": _get_job_field(job_details, "team_info"),
            "required_skills": _get_job_field(job_details, "required_skills"),
            "responsibilities": _get_job_field(job_details, "responsibilities"),
            "seniority_level": _get_job_field(job_details, "seniority_level"),
            "hiring_manager_name": _get_job_field(job_details, "hiring_manager_name", ""),
        })

        cover_letter_content = response.content.strip()
        console.print(f"   [green]✓ Cover letter generated[/green]")

        return {
            **state,
            "cover_letter": cover_letter_content,
            "current_step": "cover_letter_generator",
        }

    except Exception as e:
        return {
            **state,
            "error": f"Cover letter generation failed: {str(e)}",
            "current_step": "cover_letter_generator"
        }


# ── Node 6: Cold Email Drafter ─────────────────────────────────

def cold_email_drafter(state: AgentState) -> AgentState:
    console.print("\n[bold cyan]► Step 6/7:[/bold cyan] Drafting cold outreach emails...")

    if state.get("error"):
        return state

    job_details = state.get("job_details", {})
    user_profile = state.get("user_profile", {})

    llm = get_llm(temperature=0.4)
    chain = COLD_EMAIL_PROMPT | llm

    try:
        response = chain.invoke({
            "user_profile": _format_profile(user_profile),
            "company_name": _get_job_field(job_details, "company_name"),
            "job_title": _get_job_field(job_details, "job_title"),
            "about_company": _get_job_field(job_details, "about_company"),
            "required_skills": _get_job_field(job_details, "required_skills"),
            "recruiter_name": _get_job_field(job_details, "recruiter_name", ""),
            "hiring_manager_name": _get_job_field(job_details, "hiring_manager_name", ""),
            "application_email": _get_job_field(job_details, "application_email", ""),
        })

        cold_email_content = response.content.strip()
        console.print(f"   [green]✓ Cold emails drafted[/green]")

        return {
            **state,
            "cold_email": cold_email_content,
            "current_step": "cold_email_drafter",
        }

    except Exception as e:
        return {
            **state,
            "error": f"Cold email drafting failed: {str(e)}",
            "current_step": "cold_email_drafter"
        }


# ── Node 7: Output Formatter ───────────────────────────────────

def output_formatter(state: AgentState) -> AgentState:
    console.print("\n[bold cyan]► Step 7/7:[/bold cyan] Saving outputs...")

    if state.get("error"):
        console.print(f"\n[bold red]✗ Pipeline failed at '{state.get('current_step')}'[/bold red]")
        console.print(f"  Error: {state.get('error')}")
        return state

    output_dir = Path(state.get("output_dir", Config.OUTPUT_DIR))
    output_dir.mkdir(parents=True, exist_ok=True)

    job_details = state.get("job_details", {})
    company = job_details.get("company_name", "company").replace(" ", "_").lower()
    role = job_details.get("job_title", "role").replace(" ", "_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    prefix = f"{company}_{role}_{timestamp}"

    files_saved = []

    # Save job details
    job_path = output_dir / f"{prefix}_job_details.json"
    job_path.write_text(json.dumps(job_details, indent=2), encoding="utf-8")
    files_saved.append(("Job Details", str(job_path)))

    # Save resume
    resume_path = output_dir / f"{prefix}_resume.md"
    resume_path.write_text(state.get("tailored_resume", ""), encoding="utf-8")
    files_saved.append(("Tailored Resume", str(resume_path)))

    # Save cover letter
    cover_path = output_dir / f"{prefix}_cover_letter.md"
    cover_path.write_text(state.get("cover_letter", ""), encoding="utf-8")
    files_saved.append(("Cover Letter", str(cover_path)))

    # Save cold emails
    email_path = output_dir / f"{prefix}_cold_emails.md"
    email_path.write_text(state.get("cold_email", ""), encoding="utf-8")
    files_saved.append(("Cold Emails", str(email_path)))

    # Save full bundle
    bundle_path = output_dir / f"{prefix}_FULL_BUNDLE.md"
    bundle_path.write_text(_build_bundle(state), encoding="utf-8")
    files_saved.append(("📦 Full Bundle", str(bundle_path)))

    _print_summary(state, files_saved)

    return {**state, "current_step": "complete"}


def _build_bundle(state: AgentState) -> str:
    job_details = state.get("job_details", {})
    candidate_name = state.get("user_profile", {}).get("personal", {}).get("name", "Candidate")

    return "\n".join([
        f"# Application Bundle",
        f"**Candidate:** {candidate_name}",
        f"**Role:** {job_details.get('job_title')} @ {job_details.get('company_name')}",
        f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        "\n---\n",
        "## Job Details",
        "```json",
        json.dumps(job_details, indent=2),
        "```",
        "\n---\n",
        state.get("tailored_resume", ""),
        "\n---\n",
        state.get("cover_letter", ""),
        "\n---\n",
        state.get("cold_email", ""),
    ])


def _print_summary(state: AgentState, files_saved: list) -> None:
    job_details = state.get("job_details", {})
    candidate_name = state.get("user_profile", {}).get("personal", {}).get("name", "Candidate")

    lines = [
        f"[bold green]✓ Application package ready![/bold green]\n",
        f"[bold]Candidate:[/bold] {candidate_name}",
        f"[bold]Role:[/bold] {job_details.get('job_title', 'N/A')}",
        f"[bold]Company:[/bold] {job_details.get('company_name', 'N/A')}",
        f"[bold]Location:[/bold] {job_details.get('location', 'N/A')}",
        "",
        "[bold]Files saved:[/bold]",
    ]
    for label, path in files_saved:
        lines.append(f"  • {label}: [dim]{path}[/dim]")

    lines.extend([
        "",
        "[bold yellow]Next steps:[/bold yellow]",
        "  1. Review resume — check Tailoring Notes at the bottom",
        "  2. Personalise the cover letter hook if needed",
        "  3. Find recruiter on LinkedIn before sending cold email",
        "  4. Apply through company portal with the tailored resume",
    ])

    console.print(Panel(
        "\n".join(lines),
        title="[bold]AI Job Application Agent[/bold]",
        border_style="green",
        padding=(1, 2),
    ))