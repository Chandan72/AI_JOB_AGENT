"""
profile_parser.py — Resume + LinkedIn PDF Parser
──────────────────────────────────────────────────
Extracts structured candidate data from:
  1. Resume PDF (any format)
  2. LinkedIn Profile PDF (exported from LinkedIn)

Uses pdfplumber for text extraction + LLM for structuring.
"""

from __future__ import annotations
import json
import re
from pathlib import Path

import pdfplumber
from langchain_core.prompts import ChatPromptTemplate

from src.config import get_llm


PROFILE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert resume parser.
Extract structured information from resume/LinkedIn text.
Return ONLY valid JSON. No markdown fences. No explanation.
If a field is not found use empty string or empty list."""),

    ("human", """Extract candidate information from this text.

RESUME/PROFILE TEXT:
─────────────────────
{raw_text}
─────────────────────

Return this exact JSON structure:
{{
  "name": "full name",
  "email": "email address",
  "phone": "phone number",
  "location": "city, country",
  "current_title": "most recent job title",
  "years_experience": 0,
  "summary": "professional summary 2-3 sentences",
  "skills": ["skill1", "skill2", "skill3"],
  "experience": [
    {{
      "company": "company name",
      "title": "job title",
      "duration": "start - end",
      "description": "brief description"
    }}
  ],
  "education": [
    {{
      "institution": "university name",
      "degree": "degree type",
      "year": "graduation year"
    }}
  ],
  "target_roles": ["role1", "role2"],
  "target_locations": ["location1", "location2"],
  "min_salary": ""
}}""")
])


SEARCH_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a job search expert who knows exactly
how to find the right jobs for a candidate. Generate search
queries that will find the most relevant job listings."""),

    ("human", """Generate 10 targeted search queries to find
INDIVIDUAL job postings (not listing pages) for this candidate.

CANDIDATE PROFILE:
{profile}

Rules for queries:
1. Each query must find a SINGLE job posting page
2. Target their exact seniority level explicitly
3. Include startup-specific terms (seed, series A, YC, funded)
4. Mix role titles with specific skills
5. Keep queries under 8 words each
6. Focus on roles matching their experience level

Examples of GOOD queries (find individual postings):
  "Data Scientist LangChain startup 2025"
  "ML Engineer RAG production India remote"
  "AI Engineer LangGraph YC startup"
  "NLP Engineer HuggingFace Series A"
  "Generative AI Engineer startup India"

Examples of BAD queries (find listing pages):
  "data scientist jobs"         ← too broad
  "best AI companies hiring"    ← finds lists
  "top machine learning jobs"   ← finds aggregators

Return ONLY a JSON array of exactly 10 query strings.
No markdown. No explanation.""")
])


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts all text from a PDF file.
    Tries three methods in order of reliability:
      Method 1: PyMuPDF text extraction (fast, works on most PDFs)
      Method 2: PyMuPDF with OCR (for image-based PDFs)
      Method 3: pdfplumber fallback
    """
    import fitz  # PyMuPDF

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # ── Method 1: PyMuPDF direct text extraction ───────────────
    text_parts = []
    doc = fitz.open(pdf_path)

    for page in doc:
        text = page.get_text("text")
        if text and text.strip():
            text_parts.append(text)

    doc.close()
    full_text = "\n\n".join(text_parts).strip()

    if len(full_text) >= 50:
        print(f"   ✓ Extracted {len(full_text)} characters "
              f"(Method 1 — direct)")
        return full_text

    # ── Method 2: PyMuPDF with text blocks ────────────────────
    print("   Direct extraction returned little text — "
          "trying block extraction...")
    text_parts = []
    doc = fitz.open(pdf_path)

    for page in doc:
        blocks = page.get_text("blocks")
        for block in blocks:
            if block[6] == 0:  # text block (not image)
                text_parts.append(block[4])

    doc.close()
    full_text = "\n".join(text_parts).strip()

    if len(full_text) >= 50:
        print(f"   ✓ Extracted {len(full_text)} characters "
              f"(Method 2 — blocks)")
        return full_text

    # ── Method 3: PyMuPDF raw dict extraction ─────────────────
    print("   Trying raw dictionary extraction...")
    text_parts = []
    doc = fitz.open(pdf_path)

    for page in doc:
        raw = page.get_text("rawdict")
        for block in raw.get("blocks", []):
            if block.get("type") == 0:  # text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        t = span.get("text", "").strip()
                        if t:
                            text_parts.append(t)

    doc.close()
    full_text = " ".join(text_parts).strip()

    if len(full_text) >= 50:
        print(f"   ✓ Extracted {len(full_text)} characters "
              f"(Method 3 — rawdict)")
        return full_text

    # ── Method 4: pdfplumber fallback ─────────────────────────
    print("   Trying pdfplumber fallback...")
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        full_text = "\n\n".join(text_parts).strip()
        if len(full_text) >= 50:
            print(f"   ✓ Extracted {len(full_text)} characters "
                  f"(Method 4 — pdfplumber)")
            return full_text
    except Exception:
        pass

    # ── All methods failed — PDF is truly image-only ───────────
    raise ValueError(
        f"Could not extract text from {Path(pdf_path).name} "
        f"using any method.\n\n"
        f"Your PDF appears to be fully image-based (scanned).\n\n"
        f"Please do ONE of these:\n"
        f"  Option A: Open the PDF in Word/Google Docs and "
        f"re-save as PDF\n"
        f"  Option B: Copy your resume text and save as a "
        f"new PDF using any word processor\n"
        f"  Option C: Use the sample_profile.json directly "
        f"(already has your data)"
    )

def parse_candidate_profile(
    resume_path: str,
    linkedin_path: str = None,
) -> dict:
    """
    Parses resume PDF and optionally LinkedIn PDF into
    a structured candidate profile.

    Args:
        resume_path:   Path to resume PDF
        linkedin_path: Path to LinkedIn PDF (optional)

    Returns:
        Structured candidate profile dict
    """
    # ── Extract text from PDFs ─────────────────────────────────
    resume_text = extract_text_from_pdf(resume_path)

    combined_text = resume_text
    if linkedin_path and Path(linkedin_path).exists():
        linkedin_text = extract_text_from_pdf(linkedin_path)
        combined_text = (
            f"=== RESUME ===\n{resume_text}\n\n"
            f"=== LINKEDIN PROFILE ===\n{linkedin_text}"
        )

    # ── Extract structure with LLM ────────────────────────────
    llm   = get_llm(temperature=0.0)
    chain = PROFILE_EXTRACTION_PROMPT | llm

    response = chain.invoke({"raw_text": combined_text[:6000]})
    raw_json = response.content.strip()

    # Strip markdown fences if present
    if raw_json.startswith("```"):
        raw_json = raw_json.split("```")[1]
        if raw_json.startswith("json"):
            raw_json = raw_json[4:]

    profile = json.loads(raw_json)
    return profile


def extract_skill_keywords(profile: dict) -> list[str]:
    """
    Extracts must-have skill keywords from the profile
    for the keyword pre-filter stage.

    Returns top 15 most important skills.
    """
    skills = profile.get("skills", [])

    # Also extract skills from experience descriptions
    experience = profile.get("experience", [])
    for exp in experience:
        desc = exp.get("description", "")
        # Common tech keywords extraction
        tech_pattern = r'\b(Python|SQL|Java|JavaScript|TypeScript|' \
                      r'LangChain|LangGraph|PyTorch|TensorFlow|' \
                      r'FastAPI|Docker|Kubernetes|AWS|GCP|Azure|' \
                      r'RAG|LLM|NLP|ML|AI|MLflow|Spark|Kafka)\b'
        found = re.findall(tech_pattern, desc, re.IGNORECASE)
        skills.extend(found)

    # Deduplicate and take top 15
    seen = set()
    unique_skills = []
    for s in skills:
        s_lower = s.lower().strip()
        if s_lower not in seen and len(s_lower) > 1:
            seen.add(s_lower)
            unique_skills.append(s.strip())

    return unique_skills[:15]


def generate_search_queries(profile: dict) -> list[str]:
    """
    Uses LLM to generate 10 targeted search queries
    based on the candidate profile.
    """
    llm   = get_llm(temperature=0.3)
    chain = SEARCH_QUERY_PROMPT | llm

    profile_summary = json.dumps({
        "name":           profile.get("name", ""),
        "current_title":  profile.get("current_title", ""),
        "years_exp":      profile.get("years_experience", 0),
        "top_skills":     profile.get("skills", [])[:10],
        "target_roles":   profile.get("target_roles", []),
        "location":       profile.get("location", ""),
        "target_locations": profile.get("target_locations", []),
    }, indent=2)

    response = chain.invoke({"profile": profile_summary})
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    queries = json.loads(raw)
    return queries[:10]