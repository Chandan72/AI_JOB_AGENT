"""
hunter_main.py — Job Hunter CLI Entry Point

Usage:
  # Start scheduler (runs daily at 10 AM)
  python hunter_main.py start

  # Run once right now (for testing)
  python hunter_main.py run-now

  # Run once with custom paths
  python hunter_main.py run-now --resume ./my_resume.pdf

  # Check tracker stats
  python hunter_main.py stats
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

app     = typer.Typer(
    name="job-hunter",
    help="🎯 AI Job Hunter — Finds top 20 matched jobs every morning",
    add_completion=False,
)
console = Console()


def _print_banner():
    console.print(Panel.fit(
        "[bold cyan]🎯 AI Job Hunter Agent[/bold cyan]\n"
        "[dim]Finds your top 20 matched jobs every morning at 10 AM[/dim]\n"
        "[dim]LinkedIn · Indeed · Naukri · Wellfound · YC Jobs[/dim]",
        border_style="cyan",
        padding=(0, 4),
    ))
    console.print()


@app.command()
def start(
    resume: str = typer.Option(
        "./candidate_data/resume.pdf",
        "--resume", "-r",
        help="Path to your resume PDF",
    ),
    linkedin: str = typer.Option(
        "./candidate_data/linkedin.pdf",
        "--linkedin", "-l",
        help="Path to your LinkedIn profile PDF",
    ),
    run_now: bool = typer.Option(
        False,
        "--run-now",
        help="Run immediately then continue on schedule",
    ),
):
    """Start the daily 10 AM job hunting scheduler."""
    _print_banner()
    _validate_files(resume, linkedin)

    from job_hunter.scheduler import start_scheduler
    start_scheduler(resume, linkedin, run_now=run_now)


@app.command()
def run_now(
    resume: str = typer.Option(
        "./candidate_data/resume.pdf",
        "--resume", "-r",
        help="Path to your resume PDF",
    ),
    linkedin: str = typer.Option(
        "./candidate_data/linkedin.pdf",
        "--linkedin", "-l",
        help="Path to your LinkedIn profile PDF",
    ),
):
    """Run the job hunter once right now (for testing)."""
    _print_banner()
    _validate_files(resume, linkedin)

    from job_hunter.scheduler import run_job_hunter
    run_job_hunter(resume_path=resume, linkedin_path=linkedin)


@app.command()
def stats():
    """Show job tracker statistics."""
    from job_hunter.tracker import get_stats
    s = get_stats()
    console.print(Panel(
        f"[bold]Total jobs tracked:[/bold] "
        f"{s['total_jobs_tracked']}\n"
        f"[bold]Total daily runs:[/bold] {s['total_runs']}",
        title="Job Hunter Stats",
        border_style="cyan",
    ))


def _validate_files(resume: str, linkedin: str) -> None:
    """Validates that input files exist."""
    if not Path(resume).exists():
        console.print(
            f"[bold red]✗ Resume not found:[/bold red] {resume}\n"
            f"  Place your resume PDF at: ./candidate_data/resume.pdf"
        )
        raise typer.Exit(1)

    if not Path(linkedin).exists():
        console.print(
            f"[yellow]⚠ LinkedIn PDF not found:[/yellow] {linkedin}\n"
            f"  Continuing with resume only.\n"
            f"  [dim]Export from LinkedIn → Me → View Profile "
            f"→ More → Save to PDF[/dim]"
        )


if __name__ == "__main__":
    app()


