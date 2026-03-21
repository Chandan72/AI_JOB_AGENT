"""
job_scraper.py — Multi-Platform Job Scraper
─────────────────────────────────────────────
Searches LinkedIn, Indeed, Naukri, Wellfound, and YC Jobs
using Tavily search API.

Design: runs all platform searches in sequence,
aggregates results into a unified JobListing format.
"""

from __future__ import annotations
import re
from datetime import datetime

from tavily import TavilyClient
from src.config import Config


# ── Platform search templates ──────────────────────────────────
PLATFORM_CONFIGS = [
    {
        "name":   "LinkedIn",
        "prefix": "site:linkedin.com/jobs",
        "weight": 1.0,
    },
    {
        "name":   "Indeed",
        "prefix": "site:indeed.com jobs",
        "weight": 0.9,
    },
    {
        "name":   "Naukri",
        "prefix": "site:naukri.com",
        "weight": 0.9,
    },
    {
        "name":   "Wellfound",
        "prefix": "site:wellfound.com jobs",
        "weight": 0.85,
    },
    {
        "name":   "YC Jobs",
        "prefix": "site:workatastartup.com",
        "weight": 0.85,
    },
]


def scrape_jobs(
    search_queries: list[str],
    max_results_per_query: int = 5,
) -> list[dict]:
    """
    Searches all configured job platforms for each query.

    Args:
        search_queries:        List of search queries from profile parser
        max_results_per_query: Results per query per platform

    Returns:
        List of raw job listing dicts (before deduplication/filtering)
    """
    client   = TavilyClient(api_key=Config.TAVILY_API_KEY)
    all_jobs = []
    seen_urls = set()

    print(f"\n   Searching {len(PLATFORM_CONFIGS)} platforms "
          f"× {len(search_queries)} queries...")

    for query in search_queries:
        for platform in PLATFORM_CONFIGS:
            # Build platform-specific search query
            search_term = f"{platform['prefix']} {query}"

            try:
                results = client.search(
                    query=search_term,
                    search_depth="basic",
                    max_results=max_results_per_query,
                )

                for r in results.get("results", []):
                    url = r.get("url", "")

                    # Skip duplicates
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Skip non-job pages
                    if not _is_job_listing(url, r.get("title", "")):
                        continue

                    job = _normalise_result(r, platform["name"])
                    if job:
                        all_jobs.append(job)

            except Exception as e:
                print(f"   ⚠ {platform['name']} search failed "
                      f"for '{query[:30]}...': {str(e)[:50]}")
                continue

    print(f"   ✓ Scraped {len(all_jobs)} raw job listings")
    return all_jobs


def _is_job_listing(url: str, title: str) -> bool:
    """
    Filters out non-job pages (company homepages, blog posts etc.)
    """
    # Must have job-related signals in URL or title
    job_url_signals = [
        "/jobs/", "/job/", "/careers/", "/opening",
        "/position", "job_id=", "jk=",
        "wellfound.com/l/", "workatastartup"
    ]
    job_title_signals = [
        "engineer", "developer", "scientist", "analyst",
        "manager", "designer", "architect", "lead",
        "intern", "associate", "director", "consultant"
    ]

    url_lower   = url.lower()
    title_lower = title.lower()

    has_url_signal   = any(s in url_lower for s in job_url_signals)
    has_title_signal = any(s in title_lower for s in job_title_signals)

    return has_url_signal or has_title_signal


def _normalise_result(result: dict, source: str) -> dict | None:
    """
    Converts a raw Tavily result into our JobListing format.
    """
    title   = result.get("title", "").strip()
    url     = result.get("url", "").strip()
    content = result.get("content", "").strip()

    if not title or not url:
        return None

    # Extract company name from title or URL
    company = _extract_company(title, url, source)

    # Extract location if mentioned
    location = _extract_location(content + " " + title)

    return {
        "title":       _clean_job_title(title),
        "company":     company,
        "location":    location,
        "url":         url,
        "description": content[:1000],
        "source":      source,
        "match_score": 0.0,
        "match_reason": "",
        "salary":      _extract_salary(content),
        "posted_date": datetime.now().strftime("%Y-%m-%d"),
        "job_type":    _extract_job_type(content + title),
    }


def _clean_job_title(title: str) -> str:
    """Removes platform suffixes from job titles."""
    suffixes = [
        " - LinkedIn", " | LinkedIn", " at LinkedIn",
        " - Indeed", " | Indeed",
        " - Naukri", " | Naukri",
        " - Wellfound", " | Wellfound",
        " - Work at a Startup",
    ]
    for suffix in suffixes:
        title = title.replace(suffix, "")
    return title.strip()


def _extract_company(title: str, url: str, source: str) -> str:
    """Extracts company name from job title or URL."""
    # Pattern: "Job Title at Company Name"
    at_match = re.search(r" at ([^|–\-]+)$", title, re.IGNORECASE)
    if at_match:
        return at_match.group(1).strip()

    # Pattern: "Company Name - Job Title"
    dash_match = re.match(r"^([^–\-|]+)\s*[-–|]", title)
    if dash_match:
        potential = dash_match.group(1).strip()
        # Make sure it is not the job title itself
        if len(potential.split()) <= 4:
            return potential

    return "Unknown Company"


def _extract_location(text: str) -> str:
    """Extracts location mentions from job text."""
    # Common location patterns
    locations = [
        r"(Bengaluru|Bangalore|Mumbai|Delhi|Hyderabad|Pune|Chennai)",
        r"(Remote|Work from home|WFH|Hybrid)",
        r"(India|USA|UK|Singapore|Dubai)",
        r"(\w+,\s*India)",
    ]
    for pattern in locations:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return "Location not specified"


def _extract_salary(text: str) -> str:
    """Extracts salary information if present."""
    patterns = [
        r"₹[\d,.]+\s*[-–]\s*₹[\d,.]+\s*(?:LPA|L|Lakhs?)?",
        r"\$[\d,]+\s*[-–]\s*\$[\d,]+",
        r"[\d]+\s*[-–]\s*[\d]+\s*LPA",
        r"[\d]+\s*LPA",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return ""


def _extract_job_type(text: str) -> str:
    """Extracts job type (Full-time, Remote, Contract etc.)"""
    text_lower = text.lower()
    if "remote" in text_lower:
        return "Remote"
    if "hybrid" in text_lower:
        return "Hybrid"
    if "contract" in text_lower:
        return "Contract"
    if "internship" in text_lower or "intern" in text_lower:
        return "Internship"
    return "Full-time"