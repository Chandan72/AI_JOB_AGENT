"""
— Semantic Job Matching Engine
──────────────────────────────────────────
Two-stage matching pipeline:
  Stage 1: Keyword pre-filter — fast, eliminates clearly wrong jobs
  Stage 2: Semantic re-ranking — embeddings-based deep matching

Uses sentence-transformers for embeddings (runs locally, free).
"""

from __future__ import annotations
import json
import re
import numpy as np
from langchain_core.prompts import ChatPromptTemplate
from job_app.config import get_llm


MATCH_REASON_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a career advisor explaining in 2 sentences
why a specific job is a strong match for this candidate.
Be specific — mention actual skills and experience that match.
Be honest — if it is a stretch, say so briefly.
Never use generic phrases like 'great opportunity'."""),

    ("human", """Explain in exactly 2 sentences why this job
matches this candidate.

CANDIDATE:
Name: {name}
Title: {title}
Top Skills: {skills}

JOB:
Title: {job_title}
Company: {company}
Description: {description}

2 sentences only. Specific. Honest.""")
])


def keyword_prefilter(
    jobs: list[dict],
    skill_keywords: list[str],
    min_keyword_matches: int = 1,
) -> list[dict]:
    """
    Stage 1: Fast keyword filter.
    Keeps jobs that mention at least min_keyword_matches
    skills from the candidate's profile.

    Args:
        jobs:                 Raw job listings
        skill_keywords:       Candidate's key skills
        min_keyword_matches:  Minimum skills that must match

    Returns:
        Filtered job listings
    """
    if not skill_keywords:
        return jobs

    # Build pattern from top 10 keywords
    top_keywords = skill_keywords[:10]
    pattern = re.compile(
        r'\b(' + '|'.join(re.escape(k) for k in top_keywords) + r')\b',
        re.IGNORECASE
    )

    filtered = []
    for job in jobs:
        # Search in title + description
        search_text = (
            job.get("title", "") + " " +
            job.get("description", "")
        )
        matches = pattern.findall(search_text)
        unique_matches = set(m.lower() for m in matches)

        if len(unique_matches) >= min_keyword_matches:
            job["_keyword_matches"] = list(unique_matches)
            filtered.append(job)

    print(f"   ✓ Keyword filter: {len(filtered)}/{len(jobs)} "
          f"jobs passed")
    return filtered


def semantic_rank(
    jobs: list[dict],
    candidate_profile: dict,
    top_n: int = 20,
) -> list[dict]:
    """
    Stage 2: Semantic ranking using sentence-transformers.
    Embeds candidate profile and each job description,
    then ranks by cosine similarity.

    Args:
        jobs:              Keyword-filtered job listings
        candidate_profile: Structured candidate profile
        top_n:             Number of top jobs to return

    Returns:
        Top N jobs ranked by semantic match score
    """
    if not jobs:
        return []

    print(f"   Loading embedding model...")

    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity

        model = SentenceTransformer("all-MiniLM-L6-v2")

        # ── Build candidate text representation ────────────────
        candidate_text = _build_candidate_text(candidate_profile)

        # ── Build job text representations ─────────────────────
        job_texts = [
            _build_job_text(job) for job in jobs
        ]

        # ── Compute embeddings ─────────────────────────────────
        print(f"   Computing embeddings for "
              f"{len(jobs)} jobs...")

        candidate_embedding = model.encode(
            [candidate_text], normalize_embeddings=True
        )
        job_embeddings = model.encode(
            job_texts, normalize_embeddings=True,
            show_progress_bar=False
        )

        # ── Compute similarity scores ──────────────────────────
        similarities = cosine_similarity(
            candidate_embedding, job_embeddings
        )[0]

        # ── Attach scores and sort ─────────────────────────────
        for i, job in enumerate(jobs):
            job["match_score"] = float(similarities[i])

        ranked = sorted(
            jobs,
            key=lambda j: j["match_score"],
            reverse=True
        )

        top_jobs = ranked[:top_n]
        print(f"   ✓ Semantic ranking complete — "
              f"top score: {top_jobs[0]['match_score']:.2f}")

        return top_jobs

    except ImportError:
        print("   ⚠ sentence-transformers not available — "
              "falling back to keyword scoring")
        return _keyword_score_fallback(jobs, candidate_profile, top_n)


def generate_match_reasons(
    jobs: list[dict],
    candidate_profile: dict,
) -> list[dict]:
    """
    Uses LLM to generate a specific 2-sentence explanation
    for why each of the top jobs matches the candidate.
    Runs on top 20 jobs only — controlled LLM cost.
    """
    llm   = get_llm(temperature=0.2)
    chain = MATCH_REASON_PROMPT | llm

    candidate_name   = candidate_profile.get("name", "Candidate")
    candidate_title  = candidate_profile.get("current_title", "")
    candidate_skills = ", ".join(
        candidate_profile.get("skills", [])[:8]
    )

    print(f"   Generating match explanations for "
          f"{len(jobs)} jobs...")

    for job in jobs:
        try:
            response = chain.invoke({
                "name":        candidate_name,
                "title":       candidate_title,
                "skills":      candidate_skills,
                "job_title":   job.get("title", ""),
                "company":     job.get("company", ""),
                "description": job.get("description", "")[:500],
            })
            job["match_reason"] = response.content.strip()
        except Exception:
            job["match_reason"] = (
                f"Strong skills overlap with {job.get('title', 'role')} "
                f"requirements based on your profile."
            )

    return jobs


def _build_candidate_text(profile: dict) -> str:
    """
    Converts candidate profile into a rich text representation
    for embedding. More detail = better matching.
    """
    parts = [
        f"Job Title: {profile.get('current_title', '')}",
        f"Experience: {profile.get('years_experience', 0)} years",
        f"Summary: {profile.get('summary', '')}",
        f"Skills: {', '.join(profile.get('skills', []))}",
        f"Target Roles: {', '.join(profile.get('target_roles', []))}",
    ]

    for exp in profile.get("experience", [])[:2]:
        parts.append(
            f"Previous Role: {exp.get('title', '')} "
            f"at {exp.get('company', '')}"
        )

    return " | ".join(filter(None, parts))


def _build_job_text(job: dict) -> str:
    """Converts job listing into text for embedding."""
    return (
        f"Job Title: {job.get('title', '')} | "
        f"Company: {job.get('company', '')} | "
        f"Location: {job.get('location', '')} | "
        f"Description: {job.get('description', '')[:300]}"
    )


def _keyword_score_fallback(
    jobs: list[dict],
    profile: dict,
    top_n: int,
) -> list[dict]:
    """Fallback if sentence-transformers unavailable."""
    skills = set(s.lower() for s in profile.get("skills", []))
    for job in jobs:
        text = (
            job.get("title", "") + " " +
            job.get("description", "")
        ).lower()
        matches = sum(1 for s in skills if s in text)
        job["match_score"] = min(matches / max(len(skills), 1), 1.0)

    return sorted(
        jobs, key=lambda j: j["match_score"], reverse=True
    )[:top_n]