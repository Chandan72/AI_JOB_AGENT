"""
digest_generator.py — Daily Job Digest Builder
────────────────────────────────────────────────
Generates a beautiful HTML email digest of the top 20 jobs.
Also saves an HTML file for local review.
"""

from __future__ import annotations
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from job_app.config import Config


def generate_html_digest(
    jobs: list[dict],
    candidate_name: str,
    run_date: str,
) -> str:
    """
    Generates a clean, professional HTML email
    with all 20 matched jobs.
    """
    job_cards = ""
    for i, job in enumerate(jobs, 1):
        score_pct  = int(job.get("match_score", 0) * 100)
        score_color = (
            "#22c55e" if score_pct >= 80 else
            "#f59e0b" if score_pct >= 60 else
            "#6b7280"
        )

        salary_html = ""
        if job.get("salary"):
            salary_html = f"""
            <span style="background:#f0fdf4;color:#166534;
                padding:2px 8px;border-radius:4px;
                font-size:12px;margin-left:8px;">
                {job['salary']}
            </span>"""

        job_cards += f"""
        <div style="background:white;border:1px solid #e5e7eb;
            border-radius:12px;padding:20px;margin-bottom:16px;
            box-shadow:0 1px 3px rgba(0,0,0,0.05);">

            <div style="display:flex;justify-content:space-between;
                align-items:flex-start;margin-bottom:12px;">
                <div>
                    <span style="background:#f3f4f6;color:#6b7280;
                        font-size:11px;padding:2px 8px;
                        border-radius:4px;font-weight:500;">
                        #{i} · {job.get('source', 'Job Board')}
                    </span>
                    {salary_html}
                </div>
                <div style="text-align:right;">
                    <span style="background:{score_color}20;
                        color:{score_color};font-weight:700;
                        font-size:13px;padding:4px 10px;
                        border-radius:6px;">
                        {score_pct}% match
                    </span>
                </div>
            </div>

            <h3 style="margin:0 0 4px;font-size:16px;
                color:#111827;font-weight:600;">
                {job.get('title', 'Unknown Role')}
            </h3>

            <p style="margin:0 0 8px;color:#6b7280;font-size:14px;">
                <strong style="color:#374151;">
                    {job.get('company', 'Unknown Company')}
                </strong>
                &nbsp;·&nbsp; {job.get('location', 'Location N/A')}
                &nbsp;·&nbsp;
                <span style="color:#8b5cf6;">
                    {job.get('job_type', 'Full-time')}
                </span>
            </p>

            <p style="margin:0 0 12px;color:#4b5563;
                font-size:13px;line-height:1.5;
                background:#f9fafb;padding:10px;
                border-radius:6px;border-left:3px solid {score_color};">
                <em>{job.get('match_reason',
                    'Strong profile match based on skills and experience.')
                }</em>
            </p>

            <a href="{job.get('url', '#')}"
                style="display:inline-block;background:#1d4ed8;
                color:white;padding:8px 16px;border-radius:6px;
                text-decoration:none;font-size:13px;font-weight:500;">
                View Job →
            </a>
        </div>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Your Daily Job Digest — {run_date}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',
    sans-serif;">

<div style="max-width:680px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1d4ed8,#7c3aed);
        border-radius:16px;padding:32px;margin-bottom:24px;
        text-align:center;">
        <h1 style="margin:0 0 8px;color:white;font-size:24px;">
            🎯 Your Daily Job Digest
        </h1>
        <p style="margin:0;color:#bfdbfe;font-size:14px;">
            {run_date} · Top {len(jobs)} matches for
            <strong>{candidate_name}</strong>
        </p>
    </div>

    <!-- Stats Bar -->
    <div style="background:white;border-radius:12px;padding:16px;
        margin-bottom:24px;display:flex;
        border:1px solid #e5e7eb;">
        <div style="flex:1;text-align:center;
            border-right:1px solid #e5e7eb;">
            <div style="font-size:24px;font-weight:700;
                color:#1d4ed8;">{len(jobs)}</div>
            <div style="font-size:12px;color:#6b7280;">Jobs Found</div>
        </div>
        <div style="flex:1;text-align:center;
            border-right:1px solid #e5e7eb;">
            <div style="font-size:24px;font-weight:700;color:#22c55e;">
                {sum(1 for j in jobs
                     if int(j.get('match_score',0)*100) >= 80)}
            </div>
            <div style="font-size:12px;color:#6b7280;">
                High Match (80%+)
            </div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="font-size:24px;font-weight:700;color:#8b5cf6;">
                {len(set(j.get('source','') for j in jobs))}
            </div>
            <div style="font-size:12px;color:#6b7280;">Platforms</div>
        </div>
    </div>

    <!-- Job Cards -->
    {job_cards}

    <!-- Footer -->
    <div style="text-align:center;padding:24px;
        color:#9ca3af;font-size:12px;">
        <p style="margin:0 0 8px;">
            Generated by your AI Job Hunter Agent
        </p>
        <p style="margin:0;">
            See a job you like? Run the main pipeline to
            generate a tailored resume and cover letter.
        </p>
    </div>

</div>
</body>
</html>"""

    return html


def save_digest_to_file(html: str, output_dir: str = "./outputs") -> str:
    """Saves the HTML digest to a file for local review."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    today    = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{output_dir}/job_digest_{today}.html"
    Path(filename).write_text(html, encoding="utf-8")
    return filename


def send_digest_email(
    html: str,
    recipient_email: str,
    candidate_name: str,
    job_count: int,
) -> tuple[bool, str]:
    """Sends the digest via Gmail SMTP."""
    today   = datetime.now().strftime("%B %d, %Y")
    subject = (
        f"🎯 {job_count} New Job Matches for You — {today}"
    )

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = (
        f"Job Hunter Agent <{Config.GMAIL_SENDER_EMAIL}>"
    )
    msg["To"]      = recipient_email

    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
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
        return True, f"Digest sent to {recipient_email}"
    except Exception as e:
        return False, str(e)