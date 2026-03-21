"""
job_scraper.py — Multi-Platform Job Scraper
─────────────────────────────────────────────
Searches Wellfound and YC Jobs for individual job postings.
Each result must be a single specific job — not an aggregated
listing page or search results page.
"""

from __future__ import annotations
import re
from datetime import datetime
from tavily import TavilyClient
from src.config import Config


# ── Platform configs ───────────────────────────────────────────
PLATFORM_CONFIGS = [
    {
        "name":   "Wellfound",
        "prefix": "site:wellfound.com/jobs",
        "weight": 1.0,
    },
    {
        "name":   "YC Jobs",
        "prefix": "site:workatastartup.com/jobs",
        "weight": 1.0,
    },
]

# ── URLs that are aggregated pages — not individual jobs ───────
BLACKLIST_PATTERNS = [
    r"wellfound\.com/jobs\?",          # search results page
    r"wellfound\.com/role/",           # role category page
    r"wellfound\.com/company/",        # company page
    r"workatastartup\.com/companies",  # companies list
    r"workatastartup\.com\?",          # search page
    r"/jobs/search",
    r"/jobs\?q=",
    r"/jobs\?location=",
    r"\d+,\d+.*jobs",                  # "1,000 jobs for..."
    r"\d+.*vacancies",                 # "500 vacancies"
    r"jobs\.lever\.co$",               # company root
    r"boards\.greenhouse\.io$",        # board root
]

# ── Titles that indicate aggregated pages ──────────────────────
BLACKLIST_TITLE_PATTERNS = [
    r"\d+[\s,]+\w+\s+jobs",           # "1000 Data Science jobs"
    r"\d+[\s,]+vacancies",
    r"jobs in \w+",                    # "Jobs in India"
    r"top \d+ companies",
    r"best companies",
    r"hiring now",
    r"job openings",
]


def scrape_jobs(
    search_queries: list[str],
    max_results_per_query: int = 5,
) -> list[dict]:
    """
    Searches Wellfound and YC Jobs for individual job postings.
    Strictly filters to single job posting URLs only.
    """
    client    = TavilyClient(api_key=Config.TAVILY_API_KEY)
    all_jobs  = []
    seen_urls = set()

    print(f"\n   Searching {len(PLATFORM_CONFIGS)} platforms "
          f"× {len(search_queries)} queries...")

    for query in search_queries:
        for platform in PLATFORM_CONFIGS:
            search_term = f"{platform['prefix']} {query}"

            try:
                results = client.search(
                    query=search_term,
                    search_depth="advanced",
                    max_results=max_results_per_query,
                )

                for r in results.get("results", []):
                    url   = r.get("url", "").strip()
                    title = r.get("title", "").strip()

                    if not url or not title:
                        continue
                    if url in seen_urls:
                        continue
                    if _is_blacklisted(url, title):
                        continue
                    if not _is_individual_job(url):
                        continue

                    seen_urls.add(url)
                    job = _normalise_result(r, platform["name"])
                    if job:
                        all_jobs.append(job)

            except Exception as e:
                print(f"   ⚠ {platform['name']} error: "
                      f"{str(e)[:60]}")
                continue

    print(f"   ✓ Scraped {len(all_jobs)} individual job postings")
    return all_jobs


def _is_blacklisted(url: str, title: str) -> bool:
    """Returns True if this URL/title looks like an aggregated page."""
    url_lower   = url.lower()
    title_lower = title.lower()

    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, url_lower):
            return True

    for pattern in BLACKLIST_TITLE_PATTERNS:
        if re.search(pattern, title_lower):
            return True

    return False


def _is_individual_job(url: str) -> bool:
    """
    Returns True only if this URL pattern indicates
    a single, specific job posting — not a list page.

    Individual job URL patterns:
      wellfound.com/jobs/12345-job-title
      wellfound.com/l/job-title/company
      workatastartup.com/jobs/12345
    """
    url_lower = url.lower()

    # Wellfound individual job: /jobs/DIGITS-slug
    if re.search(r"wellfound\.com/jobs/\d+-", url_lower):
        return True

    # Wellfound individual job: /l/ path
    if re.search(r"wellfound\.com/l/", url_lower):
        return True

    # YC individual job: /jobs/DIGITS
    if re.search(r"workatastartup\.com/jobs/\d+", url_lower):
        return True

    # Generic individual job patterns
    if re.search(
        r"/(job|position|opening|role)/[a-z0-9-]{5,}$",
        url_lower
    ):
        return True

    # Greenhouse / Lever individual jobs
    if re.search(r"boards\.greenhouse\.io/\w+/jobs/\d+", url_lower):
        return True
    if re.search(r"jobs\.lever\.co/\w+/[a-f0-9-]{30,}", url_lower):
        return True

    return False


def _normalise_result(result: dict, source: str) -> dict | None:
    """Converts a Tavily result into our JobListing format."""
    title   = result.get("title", "").strip()
    url     = result.get("url", "").strip()
    content = result.get("content", "").strip()

    if not title or not url:
        return None

    # Extract company from title or URL — more aggressive
    company = _extract_company_precise(title, url, content)

    # Skip if we cannot identify a real company
    if company in ("Unknown Company", ""):
        company = _extract_company_from_url(url)

    location = _extract_location(content + " " + title)
    salary   = _extract_salary(content)

    return {
        "title":        _clean_job_title(title),
        "company":      company,
        "location":     location,
        "url":          url,
        "description":  content[:800],
        "source":       source,
        "match_score":  0.0,
        "match_reason": "",
        "salary":       salary,
        "posted_date":  datetime.now().strftime("%Y-%m-%d"),
        "job_type":     _extract_job_type(content + title),
    }


def _extract_company_precise(
    title: str, url: str, content: str
) -> str:
    """
    Extracts company name using multiple strategies.
    Priority: title pattern > URL > content.
    """
    # Strategy 1: "Job Title at Company Name" pattern
    at_match = re.search(
        r"\bat\s+([A-Z][A-Za-z0-9\s&\.,\-]{2,40}?)(?:\s*[-|–·]|$)",
        title
    )
    if at_match:
        company = at_match.group(1).strip().rstrip(".,- ")
        if 2 <= len(company.split()) <= 6:
            return company

    # Strategy 2: "Company - Job Title" pattern
    dash_match = re.match(
        r"^([A-Z][A-Za-z0-9\s&\.,]{2,30}?)\s*[-–|]\s*",
        title
    )
    if dash_match:
        potential = dash_match.group(1).strip()
        # Verify it's not a job title keyword
        job_keywords = {
            "senior", "junior", "lead", "staff", "principal",
            "data", "software", "machine", "deep", "ai", "ml",
            "full", "back", "front", "remote", "contract"
        }
        if potential.lower().split()[0] not in job_keywords:
            return potential

    # Strategy 3: Extract from content "at Company" patterns
    content_match = re.search(
        r"(?:joining|join|at|with)\s+([A-Z][A-Za-z0-9\s&]{2,30}?)"
        r"(?:\s*,|\s+is|\s+are|\s+we|\.|$)",
        content[:300]
    )
    if content_match:
        company = content_match.group(1).strip()
        if 2 < len(company) < 40:
            return company

    return ""


def _extract_company_from_url(url: str) -> str:
    """Extracts company name from URL structure."""
    # wellfound.com/company/COMPANY-NAME
    match = re.search(r"wellfound\.com/company/([a-z0-9-]+)", url)
    if match:
        return match.group(1).replace("-", " ").title()

    # workatastartup.com/companies/COMPANY
    match = re.search(
        r"workatastartup\.com/companies/([a-z0-9-]+)", url
    )
    if match:
        return match.group(1).replace("-", " ").title()

    return "Unknown Company"


def _clean_job_title(title: str) -> str:
    """Removes platform name suffixes from job titles."""
    suffixes = [
        " - Wellfound", " | Wellfound",
        " - Work at a Startup", " | Work at a Startup",
        " - AngelList", " | AngelList",
        " - Indeed", " | Indeed",
    ]
    for suffix in suffixes:
        title = title.replace(suffix, "")

    # Remove aggregation patterns
    title = re.sub(
        r"\s*[-|]\s*\d+[\s,]+(?:jobs|openings|vacancies).*$",
        "", title, flags=re.IGNORECASE
    )
    return title.strip()


def _extract_location(text: str) -> str:
    """Extracts location from job text."""
    # Remote first — most startup jobs
    if re.search(r"\b(remote|work from home|wfh)\b", text, re.I):
        # Check if hybrid
        if re.search(r"\bhybrid\b", text, re.I):
            return "Hybrid"
        return "Remote"

    # India cities
    city_match = re.search(
        r"\b(Bengaluru|Bangalore|Mumbai|Delhi|NCR|Noida|"
        r"Gurgaon|Hyderabad|Pune|Chennai|Kolkata)\b",
        text, re.IGNORECASE
    )
    if city_match:
        city = city_match.group(1)
        return f"{city}, India"

    # US cities
    us_match = re.search(
        r"\b(San Francisco|New York|Seattle|Austin|"
        r"New York City|NYC|SF|Bay Area)\b",
        text, re.IGNORECASE
    )
    if us_match:
        return us_match.group(1)

    return "Location not specified"


def _extract_salary(text: str) -> str:
    """Extracts salary information."""
    patterns = [
        r"₹[\d,.]+\s*[-–to]+\s*₹[\d,.]+\s*(?:LPA|L|Lakhs?)?",
        r"[\d]+\s*[-–]\s*[\d]+\s*LPA",
        r"[\d]+\s*LPA",
        r"\$[\d,]+\s*[-–]\s*\$[\d,]+\s*(?:k|K)?",
        r"\$[\d]+[kK]\s*[-–]\s*\$[\d]+[kK]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""


def _extract_job_type(text: str) -> str:
    """Extracts job type."""
    text_lower = text.lower()
    if "intern" in text_lower:
        return "Internship"
    if "contract" in text_lower or "freelance" in text_lower:
        return "Contract"
    if "part-time" in text_lower or "part time" in text_lower:
        return "Part-time"
    return "Full-time"