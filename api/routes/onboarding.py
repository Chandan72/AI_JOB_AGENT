"""
 — Profile Setup Endpoints
"""
import json
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

CANDIDATE_DIR = Path("./candidate_data")
CANDIDATE_DIR.mkdir(exist_ok=True)


@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload resume PDF."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    dest = CANDIDATE_DIR / "resume.pdf"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"success": True, "message": "Resume uploaded"}


@router.post("/upload-linkedin")
async def upload_linkedin(file: UploadFile = File(...)):
    """Upload LinkedIn PDF."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    dest = CANDIDATE_DIR / "linkedin.pdf"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"success": True, "message": "LinkedIn PDF uploaded"}


@router.post("/save-profile")
async def save_profile(
    name: str = Form(...),
    email: str = Form(...),
    years_experience: int = Form(...),
    target_roles: str = Form(...),
    location: str = Form(...),
    phone: str = Form(""),
):
    """Save candidate profile from onboarding form."""
    # Parse target roles from comma-separated string
    roles = [r.strip() for r in target_roles.split(",") if r.strip()]

    # Check if profile.json already exists (from PDF parse)
    profile_path = CANDIDATE_DIR / "profile.json"
    existing = {}
    if profile_path.exists():
        with open(profile_path) as f:
            existing = json.load(f)

    # Merge form data with existing profile
    profile = {
        **existing,
        "name": name,
        "email": email,
        "years_experience": years_experience,
        "target_roles": roles,
        "location": location,
        "phone": phone,
        "target_locations": [location, "Remote"],
    }

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    # Try to parse PDF if not yet parsed
    if not existing.get("skills"):
        try:
            from job_hunter.profile_parser import parse_candidate_profile
            parsed = parse_candidate_profile(
                str(CANDIDATE_DIR / "resume.pdf"),
                str(CANDIDATE_DIR / "linkedin.pdf"),
            )
            profile = {**parsed, **profile}
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2)
        except Exception:
            pass

    return {"success": True, "profile": profile}


@router.get("/profile")
async def get_profile():
    """Get current candidate profile."""
    profile_path = CANDIDATE_DIR / "profile.json"
    if not profile_path.exists():
        return {"exists": False}
    with open(profile_path) as f:
        return {"exists": True, "profile": json.load(f)}