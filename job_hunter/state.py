"""
— Job Hunter Agent State
───────────────────────────────────
Separate state from the main pipeline.
The job hunter is an independent agent
with its own data flow.
"""

from __future__ import annotations
from typing import Optional
from typing_extensions import TypedDict


class JobListing(TypedDict, total=False):
    title: str
    company: str
    location: str
    url: str
    description: str
    source: str           # linkedin / indeed / naukri / wellfound / yc
    match_score: float    # 0.0 to 1.0
    match_reason: str     # LLM-generated explanation
    salary: str
    posted_date: str
    job_type: str


class CandidateProfile(TypedDict, total=False):
    name: str
    email: str
    phone: str
    location: str
    current_title: str
    years_experience: int
    summary: str
    skills: list[str]
    experience: list[dict]
    education: list[dict]
    target_roles: list[str]
    target_locations: list[str]
    min_salary: str


class HunterState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────
    resume_pdf_path: str
    linkedin_pdf_path: str

    # ── Candidate ──────────────────────────────────────────────
    candidate_profile: CandidateProfile
    skill_keywords: list[str]      # extracted must-have keywords
    search_queries: list[str]      # generated search queries

    # ── Jobs Pipeline ──────────────────────────────────────────
    raw_jobs: list[JobListing]         # all scraped jobs ~100-150
    fresh_jobs: list[JobListing]       # after deduplication
    filtered_jobs: list[JobListing]    # after keyword pre-filter
    ranked_jobs: list[JobListing]      # after semantic ranking
    top_jobs: list[JobListing]         # final top 20

    # ── Output ─────────────────────────────────────────────────
    digest_html: str               # beautiful HTML email
    digest_path: str               # saved file path
    email_sent: bool

    # ── Control ────────────────────────────────────────────────
    run_date: str
    error: Optional[str]
    current_step: str