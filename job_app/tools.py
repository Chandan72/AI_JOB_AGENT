from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from job_app.config import Config

JOB_CONTENT_SELECTORS = [
    # Greenhouse
    "#content",
    ".job-post",
    # Lever
    ".posting-content",
    ".posting",
    # Workday
    '[data-automation-id="jobPostingDescription"]',
    # LinkedIn
    ".description__text",
    ".show-more-less-html",
    # Indeed
    "#jobDescriptionText",
    ".jobsearch-jobDescriptionText",
    # Generic
    ".job-description",
    ".job-details",
    ".job-content",
    ".description",
    "#job-description",
    "#description",
    "article",
    "main",
]


def fetch_job_posting(url: str) -> tuple[str, str]:
    headers = {
        "User-Agent": Config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=Config.REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return (
            "",
            f"Request timed out after {Config.REQUEST_TIMEOUT}s. Try pasting the JD text directly.",
        )
    except requests.exceptions.ConnectionError:
        return "", f"Could not connect to {url}. Check the URL or paste the JD text."
    except requests.exceptions.HTTPError as e:
        return "", f"HTTP {e.response.status_code} error fetching {url}."
    except Exception as e:
        return "", f"Unexpected error fetching URL: {str(e)}"

    soup = BeautifulSoup(response.text, "lxml")

    for tag in soup.find_all(
        ["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript", "meta"]
    ):
        tag.decompose()

    content_element = None
    for selector in JOB_CONTENT_SELECTORS:
        found = soup.select(selector)
        if found:
            content_element = max(found, key=lambda el: len(el.get_text()))
            if len(content_element.get_text(strip=True)) > 200:
                break

    if content_element:
        raw_text = content_element.get_text(separator="\n", strip=True)
    else:
        body = soup.find("body")
        raw_text = body.get_text(separator="\n", strip=True) if body else soup.get_text()

    cleaned = _clean_text(raw_text)

    if len(cleaned) < 100:
        return "", "Extracted content too short. Paste the JD text directly."

    return f"[Source URL: {url}]\n\n{cleaned}", ""


def _clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    noise_patterns = [
        r"we use cookies.*?\n",
        r"accept all cookies.*?\n",
        r"privacy policy.*?\n",
        r"terms of service.*?\n",
        r"©.*?\d{4}.*?\n",
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text.strip()


def detect_input_type(job_input: str) -> str:
    stripped = job_input.strip()
    url_pattern = re.compile(r"^https?://" r"[^\s/$.?#]" r"[^\s]*$", re.IGNORECASE)
    return "url" if url_pattern.match(stripped) else "text"
