"""
 — Input Validation
Validates job description input before running pipeline.
"""

import re


def validate_jd(text: str) -> tuple[bool, str]:
    """
    Validates job description text.
    Returns (is_valid, error_message).
    """
    text = text.strip()

    if len(text) < 100:
        return False, (
            "Too short. Paste the full job description "
            "(minimum 100 characters)."
        )

    if len(text) > 15000:
        return False, (
            "Too long. Paste only the job description text."
        )

    # Basic prompt injection check
    injections = [
        r"ignore previous instructions",
        r"disregard.*instructions",
        r"you are now",
        r"jailbreak",
    ]
    for pattern in injections:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "Invalid input detected."

    # Must contain job-related words
    signals = [
        "experience", "skills", "responsibilities",
        "requirements", "role", "position", "job",
        "engineer", "scientist", "developer", "manager",
        "analyst", "team", "qualifications", "hiring",
    ]
    if not any(s in text.lower() for s in signals):
        return False, (
            "This does not look like a job description. "
            "Please paste the full job posting text."
        )

    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    """Validates an email address."""
    if not email or "@" not in email:
        return False, "Invalid email address."
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email.strip()):
        return False, "Invalid email format."
    return True, ""