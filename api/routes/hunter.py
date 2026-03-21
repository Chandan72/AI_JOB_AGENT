"""
— Job Hunting Endpoints
"""
import json
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks
from datetime import datetime

router = APIRouter(prefix="/api/hunter", tags=["hunter"])

# Store last hunt results in memory
_last_results: dict = {"jobs": [], "run_date": "", "total": 0}


@router.post("/run")
async def run_hunter(background_tasks: BackgroundTasks):
    """
    Trigger job hunter immediately.
    Runs in background — poll /status for results.
    """
    global _last_results
    _last_results["running"] = True
    _last_results["progress"] = "Starting..."

    background_tasks.add_task(_run_hunter_task)
    return {"success": True, "message": "Job hunter started"}


@router.get("/status")
async def get_status():
    """Get current hunt status and results."""
    return _last_results


@router.get("/results")
async def get_results():
    """Get the last hunt results."""
    return {
        "success": True,
        "jobs": _last_results.get("jobs", []),
        "run_date": _last_results.get("run_date", ""),
        "total_scraped": _last_results.get("total_scraped", 0),
        "message": _last_results.get("message", ""),
    }


async def _run_hunter_task():
    """Background task that runs the full hunter pipeline."""
    global _last_results

    try:
        profile_path = Path("./candidate_data/profile.json")
        if not profile_path.exists():
            _last_results = {
                "running": False,
                "success": False,
                "message": "Profile not found. Complete onboarding first.",
                "jobs": [],
            }
            return

        _last_results["progress"] = "Loading profile..."

        from job_hunter.graph import job_hunter_graph

        initial_state = {
            "resume_pdf_path":   "./candidate_data/resume.pdf",
            "linkedin_pdf_path": "./candidate_data/linkedin.pdf",
            "current_step":      "init",
            "error":             None,
        }

        _last_results["progress"] = "Searching job platforms..."
        final_state = job_hunter_graph.invoke(initial_state)

        if final_state.get("error"):
            _last_results = {
                "running": False,
                "success": False,
                "message": final_state["error"],
                "jobs": [],
            }
            return

        # Convert jobs to serializable format
        top_jobs = final_state.get("top_jobs", [])
        jobs_data = []
        for job in top_jobs:
            jobs_data.append({
                "title":           job.get("title", ""),
                "company":         job.get("company", ""),
                "url":             job.get("url", ""),
                "location":        job.get("location", ""),
                "job_type":        job.get("job_type", "Full-time"),
                "source":          job.get("source", ""),
                "match_score":     round(job.get("match_score", 0) * 100),
                "match_reason":    job.get("match_reason", ""),
                "salary":          job.get("salary", ""),
                "description":     job.get("description", "")[:300],
                "recruiter_email": "",
                "manager_email":   "",
            })

        _last_results = {
            "running":       False,
            "success":       True,
            "jobs":          jobs_data,
            "run_date":      datetime.now().strftime("%B %d, %Y at %H:%M"),
            "total_scraped": len(final_state.get("raw_jobs", [])),
            "message":       f"Found {len(jobs_data)} matches",
            "progress":      "Complete",
            "digest_path":   final_state.get("digest_path", ""),
        }

    except Exception as e:
        _last_results = {
            "running": False,
            "success": False,
            "message": str(e),
            "jobs": [],
            "progress": "Failed",
        }