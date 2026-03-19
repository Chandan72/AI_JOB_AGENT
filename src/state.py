from __future__ import annotations

from typing import Optional

from typing_extensions import TypedDict


class JobDetails(TypedDict, total=False):
    company_name: str
    job_title: str
    job_url: str
    location: str
    job_type: str
    required_skills: list[str]
    preferred_skills: list[str]
    responsibilities: list[str]
    requirements: list[str]
    salary_range: str
    about_company: str
    team_info: str
    recruiter_name: str
    hiring_manager_name: str
    application_email: str
    tech_stack: list[str]
    seniority_level: str
    industry: str


class AgentState(TypedDict, total=False):
    job_input: str
    input_type: str
    user_profile: dict
    raw_job_content: str
    job_details: JobDetails
    tailored_resume: str
    cover_letter: str
    cold_email: str
    error: Optional[str]
    current_step: str
    output_dir: str


