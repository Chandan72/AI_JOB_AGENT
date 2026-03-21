"""
scheduler.py — Daily 10 AM Job Hunt Scheduler
───────────────────────────────────────────────
Runs the job hunter pipeline every day at 10:00 AM.
Uses APScheduler — no cron setup needed, works on Windows/Mac/Linux.
"""

from __future__ import annotations
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console

console = Console()


def run_job_hunter(
    resume_path: str = "./candidate_data/resume.pdf",
    linkedin_path: str = "./candidate_data/linkedin.pdf",
) -> None:
    """Executes the full job hunting pipeline."""
    from job_hunter.graph import job_hunter_graph

    console.print(
        f"\n[bold cyan]"
        f"{'='*50}\n"
        f"JOB HUNTER — Daily Run\n"
        f"{datetime.now().strftime('%B %d, %Y at %H:%M')}\n"
        f"{'='*50}[/bold cyan]"
    )

    initial_state = {
        "resume_pdf_path":   resume_path,
        "linkedin_pdf_path": linkedin_path,
        "current_step":      "init",
        "error":             None,
    }

    try:
        final_state = job_hunter_graph.invoke(initial_state)

        if final_state.get("error"):
            console.print(
                f"\n[bold red]✗ Run failed: "
                f"{final_state['error']}[/bold red]"
            )
        else:
            console.print(
                f"\n[bold green]✓ Run complete — "
                f"next run tomorrow at 10:00 AM[/bold green]"
            )

    except Exception as e:
        console.print(f"\n[bold red]✗ Crashed: {str(e)}[/bold red]")


def start_scheduler(
    resume_path: str,
    linkedin_path: str,
    run_now: bool = False,
) -> None:
    """
    Starts the daily scheduler.

    Args:
        resume_path:   Path to resume PDF
        linkedin_path: Path to LinkedIn PDF
        run_now:       If True, run immediately then schedule
    """
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    # Schedule daily at 10:00 AM IST
    scheduler.add_job(
        func=run_job_hunter,
        trigger=CronTrigger(hour=10, minute=0),
        kwargs={
            "resume_path":   resume_path,
            "linkedin_path": linkedin_path,
        },
        id="daily_job_hunt",
        name="Daily Job Hunter",
        replace_existing=True,
    )

    console.print(
        "\n[bold green]Job Hunter Scheduler Started[/bold green]\n"
        "  Schedule: Every day at [bold]10:00 AM IST[/bold]\n"
        "  Press Ctrl+C to stop\n"
    )

    # Run immediately if requested
    if run_now:
        console.print(
            "[dim]Running now as requested...[/dim]\n"
        )
        run_job_hunter(resume_path, linkedin_path)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        console.print(
            "\n[yellow]Scheduler stopped.[/yellow]"
        )