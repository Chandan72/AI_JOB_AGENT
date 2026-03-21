"""
Pydantic Request/Response Models
"""
from pydantic import BaseModel
from typing import Optional


class OnboardingProfile(BaseModel):
    name: str
    email: str
    years_experience: int
    target_roles: list[str]
    location: str
    phone: Optional[str] = ""


class JobCard(BaseModel):
    title: str
    company: str
    url: str
    location: str
    job_type: str
    source: str
    match_score: float
    match_reason: str
    salary: Optional[str] = ""
    recruiter_email: Optional[str] = ""
    manager_email: Optional[str] = ""
    description: Optional[str] = ""


class HuntResponse(BaseModel):
    success: bool
    jobs: list[JobCard]
    total_scraped: int
    run_date: str
    message: str


class PipelineRequest(BaseModel):
    job_url: Optional[str] = ""
    job_description: Optional[str] = ""
    company_name: Optional[str] = ""
    recruiter_email: Optional[str] = ""
    manager_email: Optional[str] = ""


class PipelineResponse(BaseModel):
    success: bool
    resume: str
    cover_letter: str
    cold_email: str
    resume_pdf_path: str
    job_details: dict
    message: str