import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

app = typer.Typer(
    name="job-agent",
    help="AI Job Application Agent - Resume, Cover Letter & Cold Email",
    add_completion=False,
)
console = Console()


def _print_banner() -> None:
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]AI Job Application Agent[/bold cyan]\n"
            "[dim]Powered by LangGraph + LangChain[/dim]\n"
            "[dim]Resume - Cover Letter - Cold Email[/dim]",
            border_style="cyan",
            padding=(0, 4),
        )
    )
    console.print()


def _load_profile(profile_path: str) -> dict:
    path = Path(profile_path)
    if not path.exists():
        console.print(f"[bold red]✗ Profile file not found:[/bold red] {profile_path}")
        raise typer.Exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.command()
def run(
    jd: str = typer.Option(
        None,
        "--jd", "-j",
        help="Paste the full job description text in quotes",
    ),
    profile: str = typer.Option(
        "sample_profile.json",
        "--profile", "-p",
        help="Path to your candidate profile JSON",
    ),
    output: str = typer.Option(
        "./outputs",
        "--output", "-o",
        help="Directory to save generated files",
    ),
     verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Print all generated content in terminal",
    ),
):
    """
    Generate tailored resume, cover letter and cold email.
    Paste the full job description using --jd.
    """
    _print_banner()

    if not jd:
        console.print("[bold red]✗ Paste a job description using --jd[/bold red]")
        console.print()
        console.print("  [dim]Example:[/dim]")
        console.print("  python main.py --jd 'Senior Data Scientist at Stripe...")
        raise typer.Exit(1)

    job_input = jd

    # ── Load profile ───────────────────────────────────────────
    console.print(f"[dim]Loading profile:[/dim] {profile}")
    try:
        user_profile = _load_profile(profile)
        candidate_name = user_profile.get("personal", {}).get("name", "Candidate")
        console.print(f"[dim]Candidate:[/dim] [bold]{candidate_name}[/bold]")
    except (json.JSONDecodeError, KeyError) as e:
        console.print(f"[bold red]✗ Invalid profile JSON:[/bold red] {e}")
        raise typer.Exit(1)

    console.print(Rule(style="dim"))

    # ── Run the graph ──────────────────────────────────────────
    from job_app.graph import job_application_graph

    initial_state = {
        "job_input": job_input,
        "user_profile": user_profile,
        "output_dir": output,
        "current_step": "init",
        "error": None,
    }

    try:
        final_state = job_application_graph.invoke(initial_state)
    except Exception as e:
        console.print(f"\n[bold red]✗ Pipeline crashed:[/bold red] {str(e)}")
        console.print("[dim]Check your API key and internet connection.[/dim]")
        raise typer.Exit(1)

    # ── Verbose output ─────────────────────────────────────────
    if verbose and not final_state.get("error"):
        console.print(Rule("Generated Resume", style="green"))
        console.print(final_state.get("tailored_resume", ""))
        console.print(Rule("Cover Letter", style="blue"))
        console.print(final_state.get("cover_letter", ""))
        console.print(Rule("Cold Emails", style="yellow"))
        console.print(final_state.get("cold_email", ""))

    if final_state.get("error"):
        raise typer.Exit(1)


@app.command()
def validate_profile(
    profile: str = typer.Argument(
        "sample_profile.json",
        help="Path to the profile JSON to validate",
    )
) -> None:
    """Check your profile JSON is valid before running."""
    try:
        data = _load_profile(profile)
    except Exception:
        raise typer.Exit(1)

    personal = data.get("personal", {})
    experience = data.get("experience", [])
    skills = data.get("skills", {})

    console.print(
        Panel(
            f"[bold green]OK: Profile valid[/bold green]\n\n"
            f"[bold]Name:[/bold] {personal.get('name', 'N/A')}\n"
            f"[bold]Location:[/bold] {personal.get('location', 'N/A')}\n"
            f"[bold]Jobs on record:[/bold] {len(experience)}\n"
            f"[bold]Technical skills:[/bold] {len(skills.get('technical', []))}\n"
            f"[bold]Tools:[/bold] {len(skills.get('tools', []))}",
            title="Profile Validation",
            border_style="green",
        )
    )


if __name__ == "__main__":
    app()
