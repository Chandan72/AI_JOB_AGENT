"""
— Resume/Cover Letter/Email Generation Endpoints
"""
import json
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks
from api.models import PipelineRequest
from langchain_core.prompts import ChatPromptTemplate
from src.config import get_llm
from src.prompts import EMAIL_REGENERATION_PROMPT
from src.email_sender import send_email


router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

_pipeline_results: dict = {}


@router.post("/generate")
async def generate_application(
    request: PipelineRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate resume, cover letter, and cold email
    for a specific job URL or description.
    """
    global _pipeline_results
    _pipeline_results = {"running": True, "progress": "Starting..."}

    background_tasks.add_task(_run_pipeline_task, request)
    return {"success": True, "message": "Pipeline started"}


@router.get("/status")
async def get_pipeline_status():
    """Get current pipeline status."""
    return _pipeline_results


async def _run_pipeline_task(request: PipelineRequest):
    """Runs the full application pipeline."""
    global _pipeline_results

    try:
        profile_path = Path("./candidate_data/profile.json")
        if not profile_path.exists():
            _pipeline_results = {
                "running": False,
                "success": False,
                "message": "Profile not found",
            }
            return

        with open(profile_path) as f:
            user_profile = json.load(f)

        _pipeline_results["progress"] = "Extracting job details..."

        from src.graph import job_application_graph

        job_input = request.job_url or request.job_description
        if not job_input:
            _pipeline_results = {
                "running": False,
                "success": False,
                "message": "Provide a job URL or description",
            }
            return

        email_target_type = (request.email_target_type or "auto").strip()
        if email_target_type not in ("auto", "Recruiter", "Hiring Manager", "skip"):
            email_target_type = "auto"

        initial_state = {
            "job_input":    job_input,
            "user_profile": user_profile,
            "output_dir":   "./outputs",
            "current_step": "init",
            "error":        None,
            
            # In web/API mode we never want to block on stdin.
            # "auto" will resolve to recruiter/hiring-manager based on extracted fields.
            "email_target_type": email_target_type,
            "skip_human_feedback_loop": True,
            "email_approved":    False,
            "email_sent":        False,
            "email_version":     1,
        }

        _pipeline_results["progress"] = "Running AI pipeline..."
        final = job_application_graph.invoke(initial_state)

        if final.get("error"):
            _pipeline_results = {
                "running": False,
                "success": False,
                "message": final["error"],
            }
            return

        ats_report = final.get("ats_report", {}) or {}
        _pipeline_results = {
            "running":         False,
            "success":         True,
            "resume":          final.get("tailored_resume", ""),
            "cover_letter":    final.get("cover_letter", ""),
            "cold_email":      final.get("cold_email", ""),
            "resume_pdf_path": final.get("resume_pdf_path", ""),
            "job_details":     final.get("job_details", {}),
            "ats_report":      ats_report,
            "ats_score_current": ats_report.get("ats_score_current", None),
            "ats_score_potential": ats_report.get("ats_score_potential", None),
            "message":         "Application package ready",
            "progress":        "Complete",
        }

    except Exception as e:
        _pipeline_results = {
            "running": False,
            "success": False,
            "message": str(e),
            "progress": "Failed",
        }
        


@router.post("/refine-email")
async def refine_email(request: dict):
    """
    Regenerates cold email based on user feedback.
    Called from the UI feedback loop.
    """
    try:
        current_email = request.get("current_email", "")
        feedback      = request.get("feedback", "")
        company_name  = request.get("company_name", "")

        if not current_email or not feedback:
            return {"success": False, "message": "Missing email or feedback"}

        # Load candidate profile for context
        profile_path = Path("./candidate_data/profile.json")
        user_profile = {}
        if profile_path.exists():
            with open(profile_path) as f:
                user_profile = json.load(f)

        llm   = get_llm(temperature=0.3)
        chain = EMAIL_REGENERATION_PROMPT | llm

        response = chain.invoke({
            "current_email":   current_email,
            "feedback":        feedback,
            "user_profile":    json.dumps(user_profile, indent=2),
            "company_context": f"Company: {company_name}",
        })

        return {
            "success":   True,
            "cold_email": response.content.strip(),
        }

    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/send-email")
async def send_cold_email(request: dict):
    """
    Sends the approved cold email via Gmail SMTP.
    Called when user clicks Approve + Send in UI.
    """
    try:
        recipient  = request.get("recipient_email", "")
        email_body = request.get("email_content", "")
        sender     = request.get("sender_name", "Job Applicant")

        if not recipient or "@" not in recipient:
            return {"success": False, "message": "Invalid recipient email"}
        if not email_body:
            return {"success": False, "message": "Email content is empty"}

        success, message = send_email(
            recipient_email=recipient,
            email_markdown=email_body,
            sender_name=sender,
        )
        return {"success": success, "message": message}

    except Exception as e:
        return {"success": False, "message": str(e)}