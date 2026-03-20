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
    COMPANY_RESEARCH_PROMPT,
    EMAIL_REGENERATION_PROMPT,
)
from src.pdf_generator import generate_resume_pdf
from src.email_sender import send_email
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

def company_researcher(state: AgentState) -> AgentState:
    """
    RAG node — retrieves real company intelligence from the web
    and structures it into actionable signals for downstream nodes.

    Retrieve  → Tavily search for recent company news + culture
    Augment   → LLM structures raw results into intelligence dict
    Generate  → intelligence stored in state for all downstream nodes
    """
    console.print(
        "\n[bold cyan]► Step 3.5/7:[/bold cyan] "
        "Researching company intelligence..."
    )

    if state.get("error"):
        return state

    job_details = state.get("job_details", {})
    company_name = job_details.get("company_name", "")
    job_title    = job_details.get("job_title", "")

    if not company_name:
        console.print(
            "   [yellow]⚠ No company name found — "
            "skipping research.[/yellow]"
        )
        return {
            **state,
            "company_intelligence": {},
            "current_step": "company_researcher",
        }

    # ── RETRIEVE — search for company intelligence ─────────────
    console.print(f"   Searching for: [bold]{company_name}[/bold]")

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=Config.TAVILY_API_KEY)

        # Run three targeted searches simultaneously
        search_queries = [
            f"{company_name} company news 2024 2025",
            f"{company_name} product launch engineering culture",
            f"{company_name} {job_title} team challenges growth",
        ]

        all_results = []
        for query in search_queries:
            results = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
            )
            for r in results.get("results", []):
                all_results.append(
                    f"Source: {r.get('url', '')}\n"
                    f"Title: {r.get('title', '')}\n"
                    f"Content: {r.get('content', '')}\n"
                )

        if not all_results:
            console.print(
                "   [yellow]⚠ No research results found — "
                "continuing with job details only.[/yellow]"
            )
            return {
                **state,
                "company_intelligence": {},
                "current_step": "company_researcher",
            }

        raw_research = "\n\n---\n\n".join(all_results)
        result_count = len(all_results)
        console.print(
            f"   [green]✓ Retrieved {result_count} "
            f"research results[/green]"
        )

    except Exception as e:
        # RAG failure is non-fatal — degrade gracefully
        console.print(
            f"   [yellow]⚠ Research retrieval failed: {str(e)}\n"
            f"   Continuing without company intelligence.[/yellow]"
        )
        return {
            **state,
            "company_intelligence": {},
            "current_step": "company_researcher",
        }

    # ── AUGMENT — structure raw results with LLM ───────────────
    console.print("   Analysing and structuring intelligence...")

    llm   = get_llm(temperature=0.1)
    chain = COMPANY_RESEARCH_PROMPT | llm

    try:
        response = chain.invoke({
            "company_name":  company_name,
            "job_title":     job_title,
            "raw_research":  raw_research,
        })

        raw_json = response.content.strip()

        # Strip markdown fences if model added them
        if raw_json.startswith("```"):
            raw_json = raw_json.split("```")[1]
            if raw_json.startswith("json"):
                raw_json = raw_json[4:]

        company_intelligence = json.loads(raw_json)

        # Log the cover letter hook so user sees value immediately
        hook = company_intelligence.get("cover_letter_hook", "")
        if hook:
            console.print(
                f"   [green]✓ Intelligence extracted[/green]"
            )
            console.print(
                f"   [dim]Cover letter hook:[/dim] "
                f"[italic]{hook[:80]}...[/italic]"
            )

        return {
            **state,
            "company_intelligence": company_intelligence,
            "current_step": "company_researcher",
        }

    except json.JSONDecodeError as e:
        console.print(
            f"   [yellow]⚠ Could not parse intelligence "
            f"JSON: {str(e)}\n"
            f"   Continuing without structured intelligence.[/yellow]"
        )
        return {
            **state,
            "company_intelligence": {},
            "current_step": "company_researcher",
        }
    except Exception as e:
        console.print(
            f"   [yellow]⚠ Intelligence structuring failed: "
            f"{str(e)}\n"
            f"   Continuing without company intelligence.[/yellow]"
        )
        return {
            **state,
            "company_intelligence": {},
            "current_step": "company_researcher",
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
            "company_context": state.get("company_intelligence", {}).get(
        "relevance_to_role", "Not available"
    ),
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
            "company_intelligence": json.dumps(
        state.get("company_intelligence", {}), indent=2
    ),
    "cover_letter_hook": state.get(
        "company_intelligence", {}
    ).get("cover_letter_hook", ""),
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
            "cold_email_context": state.get(
        "company_intelligence", {}
    ).get("cold_email_context", ""),
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
        
# ── Node 6.5: PDF Resume Generator ────────────────────────────

def pdf_resume_generator(state: AgentState) -> AgentState:
    """
    Converts the tailored Markdown resume into a
    professionally formatted PDF using ReportLab.
    Runs after cold_email_drafter, before output_formatter.
    """
    console.print(
        "\n[bold cyan]► Step 6.5/7:[/bold cyan] "
        "Generating PDF resume..."
    )

    if state.get("error"):
        return state

    tailored_resume = state.get("tailored_resume", "")
    if not tailored_resume:
        console.print(
            "   [yellow]⚠ No resume content found — "
            "skipping PDF generation.[/yellow]"
        )
        return {**state, "resume_pdf_path": "", "current_step": "pdf_resume_generator"}

    # ── Build output path ──────────────────────────────────────
    output_dir = Path(state.get("output_dir", "./outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)

    job_details = state.get("job_details", {})
    company  = job_details.get("company_name", "company")\
        .replace(" ", "_").lower()
    role     = job_details.get("job_title", "role")\
        .replace(" ", "_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    pdf_path  = str(output_dir / f"{company}_{role}_{timestamp}_resume.pdf")

    # ── Generate PDF ───────────────────────────────────────────
    try:
        generate_resume_pdf(
            tailored_resume_markdown=tailored_resume,
            output_path=pdf_path,
            user_profile=state.get("user_profile", {}),
        )
        console.print(
            f"   [green]✓ PDF resume saved:[/green] "
            f"[dim]{pdf_path}[/dim]"
        )
        return {
            **state,
            "resume_pdf_path": pdf_path,
            "current_step": "pdf_resume_generator",
        }

    except Exception as e:
        console.print(
            f"   [yellow]⚠ PDF generation failed: {str(e)}\n"
            f"   Markdown resume is still saved.[/yellow]"
        )
        return {
            **state,
            "resume_pdf_path": "",
            "current_step": "pdf_resume_generator",
        }
        
        
# ── Node 7: Human Feedback Loop ───────────────────────────────

def human_feedback_loop(state: AgentState) -> AgentState:
    """
    LangGraph Human-in-the-Loop node.

    Shows the generated cold email to the user in the terminal.
    Accepts three commands:
      [A] Approve — move to sending
      [F] Feedback — regenerate with instructions
      [S] Skip — save draft, do not send

    Loops until user approves or skips.
    Uses LangGraph interrupt() to pause graph execution
    and wait for real human input.
    """
    console.print("\n" + "═" * 60)
    console.print("[bold cyan]COLD EMAIL REVIEW[/bold cyan]")
    console.print("═" * 60)

    if state.get("error"):
        return state

    cold_email  = state.get("cold_email", "")
    version     = state.get("email_version", 1)
    job_details = state.get("job_details", {})
    user_profile = state.get("user_profile", {})

    # ── Display current version ────────────────────────────────
    console.print(
        f"\n[bold yellow]VERSION {version}[/bold yellow] — "
        f"{job_details.get('job_title', '')} "
        f"@ {job_details.get('company_name', '')}\n"
    )
    console.print(cold_email)
    console.print("\n" + "─" * 60)

    # ── Get user choice ────────────────────────────────────────
    console.print(
        "\n[bold]YOUR OPTIONS:[/bold]\n"
        "  [A] Approve and send this email\n"
        "  [F] Give feedback to improve it\n"
        "  [S] Skip sending — save draft only\n"
    )

    while True:
        choice = input("Your choice (A/F/S): ").strip().upper()

        if choice == "S":
            console.print(
                "\n[dim]Skipping send — "
                "email saved to outputs folder.[/dim]"
            )
            return {
                **state,
                "email_approved": False,
                "email_sent":     False,
                "current_step":   "human_feedback_loop",
            }

        elif choice == "A":
            # ── Get recipient email ────────────────────────────
            console.print()
            recipient = input(
                "Enter recipient email address: "
            ).strip()

            if not recipient or "@" not in recipient:
                console.print(
                    "[red]Invalid email address. Try again.[/red]"
                )
                continue

            console.print(
                f"\n[green]✓ Approved![/green] "
                f"Ready to send to [bold]{recipient}[/bold]"
            )
            return {
                **state,
                "email_approved":    True,
                "email_recipient":   recipient,
                "email_sent":        False,
                "current_step":      "human_feedback_loop",
            }

        elif choice == "F":
            # ── Get feedback ───────────────────────────────────
            console.print(
                "\n[dim]Examples:[/dim]\n"
                "  [dim]'Make it more casual and human'[/dim]\n"
                "  [dim]'Remove the location mention'[/dim]\n"
                "  [dim]'Make it shorter — under 50 words'[/dim]\n"
                "  [dim]'Change tone to be more confident'[/dim]\n"
            )
            feedback = input("Your feedback: ").strip()

            if not feedback:
                console.print(
                    "[yellow]No feedback entered. "
                    "Try again.[/yellow]"
                )
                continue

            # ── Regenerate with feedback ───────────────────────
            console.print(
                f"\n[bold cyan]Regenerating with your feedback...[/bold cyan]"
            )

            llm   = get_llm(temperature=0.3)
            chain = EMAIL_REGENERATION_PROMPT | llm

            try:
                company_intelligence = state.get(
                    "company_intelligence", {}
                )
                company_context = company_intelligence.get(
                    "cold_email_context", ""
                ) or company_intelligence.get("company_summary", "")

                response = chain.invoke({
                    "current_email":   cold_email,
                    "feedback":        feedback,
                    "user_profile":    _format_profile(user_profile),
                    "company_context": company_context,
                })

                new_email = response.content.strip()
                new_version = version + 1

                console.print("\n" + "═" * 60)
                console.print(
                    f"[bold cyan]VERSION {new_version} "
                    f"— Updated[/bold cyan]"
                )
                console.print("═" * 60 + "\n")
                console.print(new_email)
                console.print("\n" + "─" * 60)

                # Update state and loop again
                state = {
                    **state,
                    "cold_email":    new_email,
                    "email_version": new_version,
                    "email_feedback": feedback,
                }

                # Ask again after regeneration
                console.print(
                    "\n[bold]YOUR OPTIONS:[/bold]\n"
                    "  [A] Approve and send this email\n"
                    "  [F] Give more feedback\n"
                    "  [S] Skip sending — save draft only\n"
                )

            except Exception as e:
                console.print(
                    f"[red]Regeneration failed: {str(e)}[/red]\n"
                    f"Keeping current version."
                )

        else:
            console.print(
                "[yellow]Invalid choice. "
                "Please enter A, F, or S.[/yellow]"
            )


# ── Node 8: Gmail Sender ───────────────────────────────────────

def gmail_sender(state: AgentState) -> AgentState:
    """
    Sends the approved cold email via Gmail SMTP.
    Only runs if email_approved == True.
    Gracefully skips if user chose not to send.
    """
    console.print(
        "\n[bold cyan]► Sending email...[/bold cyan]"
    )

    if state.get("error"):
        return state

    # ── Skip if not approved ───────────────────────────────────
    if not state.get("email_approved", False):
        console.print(
            "   [dim]Email sending skipped "
            "(not approved by user).[/dim]"
        )
        return {
            **state,
            "email_sent": False,
            "current_step": "gmail_sender",
        }

    recipient    = state.get("email_recipient", "")
    cold_email   = state.get("cold_email", "")
    user_profile = state.get("user_profile", {})
    sender_name  = user_profile.get(
        "personal", {}
    ).get("name", "Job Applicant")

    # ── Send ───────────────────────────────────────────────────
    success, message = send_email(
        recipient_email=recipient,
        email_markdown=cold_email,
        sender_name=sender_name,
    )

    if success:
        console.print(
            f"   [bold green]✓ {message}[/bold green]"
        )
        return {
            **state,
            "email_sent":     True,
            "current_step":   "gmail_sender",
        }
    else:
        console.print(
            f"   [bold red]✗ Send failed: {message}[/bold red]"
        )
        return {
            **state,
            "email_sent":     False,
            "error":          f"Email send failed: {message}",
            "current_step":   "gmail_sender",
        }


# ── Node 8: Output Formatter ───────────────────────────────────

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
    
    pdf_path = state.get("resume_pdf_path", "")
    if pdf_path:
        files_saved.append(("📄 Resume PDF", pdf_path))

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
        # ── Email send status ──────────────────────────────────
        "",
        "[bold]Email status:[/bold]",
    ]

    if state.get("email_sent"):
        lines.append(
            f"  [bold green]✓ Sent to "
            f"{state.get('email_recipient', '')}[/bold green]"
        )
    elif state.get("email_approved") is False:
        lines.append(
            "  [dim]Not sent — saved as draft[/dim]"
        )
    else:
        lines.append(
            "  [dim]Pending[/dim]"
        )

    lines.extend([
        "",
        "[bold yellow]Next steps:[/bold yellow]",
        "  1. Review resume — check Tailoring Notes at the bottom",
        "  2. Personalise the cover letter hook if needed",
        "  3. Apply through company portal with the tailored resume",
    
    ])
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