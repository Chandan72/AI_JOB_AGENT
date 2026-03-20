"""
email_sender.py — Gmail SMTP Email Sender
───────────────────────────────────────────
Handles the actual sending of cold emails via Gmail SMTP.
Uses App Password authentication — no OAuth required.

Design principles:
  - Single responsibility: only sends emails, nothing else
  - Returns success/error tuple — never raises exceptions to caller
  - Validates inputs before attempting send
  - Logs all send attempts for debugging
"""

from __future__ import annotations
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.config import Config


# Gmail SMTP settings — these never change
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


def extract_subject_and_body(email_markdown: str) -> tuple[str, str]:
    """
    Extracts subject line and body from our Markdown email format.

    Our cold email format looks like:
        ## Version A — To Recruiter
        **To:** Recruiter Name
        **Subject:** Your specific subject line here

        Email body text here...

    Args:
        email_markdown: Full cold email in Markdown format

    Returns:
        Tuple of (subject, body_text)
    """
    subject = ""
    body_lines = []
    found_subject = False
    skip_header_lines = True

    lines = email_markdown.split("\n")

    for line in lines:
        stripped = line.strip()

        # Extract subject line
        if stripped.lower().startswith("**subject:**"):
            subject = re.sub(
                r"\*\*subject:\*\*\s*",
                "",
                stripped,
                flags=re.IGNORECASE
            ).strip()
            found_subject = True
            continue

        # Skip markdown headers and To/From lines
        if stripped.startswith("#"):
            continue
        if stripped.lower().startswith("**to:**"):
            continue
        if stripped.lower().startswith("**from:**"):
            continue

        # Once we have subject, start collecting body
        if found_subject:
            # Skip the separator lines
            if stripped.startswith("---"):
                continue
            skip_header_lines = False

        if not skip_header_lines and found_subject:
            # Clean markdown formatting from body
            clean_line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)  # bold
            clean_line = re.sub(r"\*(.*?)\*",     r"\1", clean_line)  # italic
            body_lines.append(clean_line)

    body = "\n".join(body_lines).strip()

    # Fallback subject if none found
    if not subject:
        subject = "Job Application — Following Up"

    return subject, body


def send_email(
    recipient_email: str,
    email_markdown: str,
    sender_name: str = "Job Applicant",
) -> tuple[bool, str]:
    """
    Sends a cold email via Gmail SMTP.

    Args:
        recipient_email: Destination email address
        email_markdown:  Full cold email content in Markdown format
        sender_name:     Display name for the sender

    Returns:
        Tuple of (success: bool, message: str)
        On success: (True, "Email sent successfully to ...")
        On failure: (False, "Error description...")
    """

    # ── Validate inputs ────────────────────────────────────────
    if not recipient_email or "@" not in recipient_email:
        return False, f"Invalid recipient email: '{recipient_email}'"

    if not Config.GMAIL_SENDER_EMAIL:
        return False, "GMAIL_SENDER_EMAIL not set in .env"

    if not Config.GMAIL_APP_PASSWORD:
        return False, "GMAIL_APP_PASSWORD not set in .env"

    # ── Extract subject and body ───────────────────────────────
    subject, body = extract_subject_and_body(email_markdown)

    if not body.strip():
        return False, "Email body is empty — cannot send."

    # ── Build MIME message ─────────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{sender_name} <{Config.GMAIL_SENDER_EMAIL}>"
    msg["To"]      = recipient_email

    # Plain text version
    text_part = MIMEText(body, "plain", "utf-8")
    msg.attach(text_part)

    # ── Send via Gmail SMTP ────────────────────────────────────
    try:
        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()            # encrypt the connection
            server.ehlo()
            server.login(
                Config.GMAIL_SENDER_EMAIL,
                Config.GMAIL_APP_PASSWORD.replace(" ", ""),
            )
            server.sendmail(
                Config.GMAIL_SENDER_EMAIL,
                recipient_email,
                msg.as_string(),
            )

        return True, f"Email sent successfully to {recipient_email}"

    except smtplib.SMTPAuthenticationError:
        return False, (
            "Gmail authentication failed. Check your App Password in .env.\n"
            "Make sure 2-Factor Auth is enabled on your Gmail account."
        )
    except smtplib.SMTPRecipientsRefused:
        return False, f"Recipient refused: {recipient_email}. Check the email address."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error sending email: {str(e)}"