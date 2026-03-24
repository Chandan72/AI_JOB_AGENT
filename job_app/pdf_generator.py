"""
pdf_generator.py — Professional Resume PDF Builder
────────────────────────────────────────────────────
Converts the tailored resume (stored in AgentState) into a
professionally formatted PDF using ReportLab.

Design matches the style of modern data science / tech resumes:
  - Clean header with name + contact bar
  - Bold section headers with horizontal rule dividers
  - Grouped skills section
  - Bullet point experience and project entries
  - Consistent typography throughout
"""

from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Table,
    TableStyle,
)
from reportlab.lib import colors


# ── Page Dimensions ────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN_LEFT   = 18 * mm
MARGIN_RIGHT  = 18 * mm
MARGIN_TOP    = 16 * mm
MARGIN_BOTTOM = 16 * mm

# ── Colour Palette ─────────────────────────────────────────────
BLACK       = colors.HexColor("#000000")
DARK_GREY   = colors.HexColor("#2C2C2C")
MID_GREY    = colors.HexColor("#555555")
LIGHT_GREY  = colors.HexColor("#888888")
RULE_COLOUR = colors.HexColor("#CCCCCC")
ACCENT      = colors.HexColor("#1A1A2E")   # deep navy — change to taste

# ── Font Sizes ─────────────────────────────────────────────────
FS_NAME     = 20
FS_CONTACT  = 8.5
FS_SECTION  = 10.5
FS_COMPANY  = 10
FS_BODY     = 9
FS_BULLET   = 9


def _styles() -> dict:
    """
    Returns a dictionary of named ParagraphStyles.
    All typography decisions live here — change once, applies everywhere.
    """
    return {
        "name": ParagraphStyle(
            "name",
            fontSize=FS_NAME,
            fontName="Helvetica-Bold",
            textColor=ACCENT,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "contact": ParagraphStyle(
            "contact",
            fontSize=FS_CONTACT,
            fontName="Helvetica",
            textColor=MID_GREY,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontSize=FS_SECTION,
            fontName="Helvetica-Bold",
            textColor=ACCENT,
            spaceBefore=10,
            spaceAfter=2,
            alignment=TA_LEFT,
        ),
        "summary": ParagraphStyle(
            "summary",
            fontSize=FS_BODY,
            fontName="Helvetica",
            textColor=DARK_GREY,
            spaceAfter=4,
            leading=13,
        ),
        "company_title": ParagraphStyle(
            "company_title",
            fontSize=FS_COMPANY,
            fontName="Helvetica-Bold",
            textColor=DARK_GREY,
            spaceBefore=6,
            spaceAfter=1,
        ),
        "company_meta": ParagraphStyle(
            "company_meta",
            fontSize=FS_BODY,
            fontName="Helvetica-Oblique",
            textColor=LIGHT_GREY,
            spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontSize=FS_BULLET,
            fontName="Helvetica",
            textColor=DARK_GREY,
            leftIndent=12,
            spaceAfter=2,
            leading=12,
            bulletIndent=4,
        ),
        "skills_label": ParagraphStyle(
            "skills_label",
            fontSize=FS_BODY,
            fontName="Helvetica-Bold",
            textColor=DARK_GREY,
            spaceAfter=1,
        ),
        "skills_value": ParagraphStyle(
            "skills_value",
            fontSize=FS_BODY,
            fontName="Helvetica",
            textColor=DARK_GREY,
            spaceAfter=3,
            leading=12,
        ),
        "education_inst": ParagraphStyle(
            "education_inst",
            fontSize=FS_COMPANY,
            fontName="Helvetica-Bold",
            textColor=DARK_GREY,
            spaceBefore=4,
            spaceAfter=1,
        ),
        "education_meta": ParagraphStyle(
            "education_meta",
            fontSize=FS_BODY,
            fontName="Helvetica",
            textColor=LIGHT_GREY,
            spaceAfter=2,
        ),
    }


def _rule(story: list) -> None:
    """Adds a thin horizontal rule — used under every section header."""
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=RULE_COLOUR,
            spaceAfter=4,
        )
    )


def _section(story: list, title: str, s: dict) -> None:
    """Adds a bold section header followed by a thin rule."""
    story.append(Paragraph(title.upper(), s["section_header"]))
    _rule(story)


def _clean(text: str) -> str:
    """
    Strips markdown formatting for ReportLab.
    ReportLab uses its own XML-like tags — raw markdown symbols
    like ** and # cause rendering issues.
    """
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)  # bold
    text = re.sub(r"\*(.*?)\*",     r"<i>\1</i>", text)  # italic
    text = re.sub(r"^#+\s*",        "",            text)  # headers
    text = re.sub(r"`(.*?)`",       r"\1",         text)  # code
    # Escape ampersands that are not already XML entities
    text = re.sub(r"&(?!amp;|lt;|gt;|quot;)", "&amp;", text)
    return text.strip()


def _parse_resume_sections(markdown_text: str) -> dict:
    """
    Parses the LLM-generated Markdown resume into a structured dict.
    Handles the section structure our resume prompt produces.

    Returns dict with keys:
      name, contact, summary, experience, skills,
      education, projects, certifications, tailoring_notes
    """
    sections = {
        "name":            "",
        "contact":         [],
        "summary":         "",
        "experience":      [],
        "skills":          [],
        "education":       [],
        "projects":        [],
        "certifications":  [],
        "tailoring_notes": [],
    }

    lines = markdown_text.split("\n")
    current_section = None
    current_block   = []

    def flush_block():
        if current_section and current_block:
            _process_block(sections, current_section, current_block[:])
        current_block.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # ── Detect section headers ────────────────────────────
        if stripped.startswith("# ") and not stripped.startswith("## "):
            # Top-level header = candidate name
            sections["name"] = stripped.lstrip("# ").strip()
            continue

        if stripped.startswith("## "):
            flush_block()
            header = stripped.lstrip("# ").strip().lower()

            if "contact"          in header: current_section = "contact"
            elif "summary"        in header: current_section = "summary"
            elif "experience"     in header: current_section = "experience"
            elif "skill"          in header: current_section = "skills"
            elif "education"      in header: current_section = "education"
            elif "project"        in header: current_section = "projects"
            elif "certification"  in header: current_section = "certifications"
            elif "tailoring"      in header: current_section = "tailoring_notes"
            else:                            current_section = None
            continue

        if current_section:
            current_block.append(stripped)

    flush_block()
    return sections


def _process_block(sections: dict, section: str, lines: list) -> None:
    """Processes raw lines for a given section into structured data."""

    if section == "contact":
        # Contact lines: email | phone | linkedin | github | location
        for line in lines:
            clean = re.sub(r"[*#]", "", line).strip()
            if clean:
                # Split on | or newlines
                parts = [p.strip() for p in re.split(r"\|", clean) if p.strip()]
                sections["contact"].extend(parts)

    elif section == "summary":
        sections["summary"] = " ".join(
            re.sub(r"^[*#\-]+\s*", "", l) for l in lines
        ).strip()

    elif section == "experience":
        _parse_experience(sections, lines)

    elif section == "skills":
        _parse_skills(sections, lines)

    elif section == "education":
        _parse_education(sections, lines)

    elif section == "projects":
        _parse_projects(sections, lines)

    elif section in ("certifications", "tailoring_notes"):
        for line in lines:
            clean = re.sub(r"^[-*•]\s*", "", line).strip()
            if clean:
                sections[section].append(clean)


def _parse_experience(sections: dict, lines: list) -> None:
    """Parses experience section into list of job dicts."""
    jobs = []
    current_job = None

    for line in lines:
        # Lines starting with ### are job titles or company headers
        if line.startswith("### ") or (
            not line.startswith("-") and
            not line.startswith("•") and
            not line.startswith("*") and
            len(line) > 3 and
            not line.startswith("|")
        ):
            if current_job:
                jobs.append(current_job)
            title_meta = re.sub(r"^#+\s*", "", line).strip()
            # Try to split "Title | Company | Duration"
            parts = [p.strip() for p in title_meta.split("|")]
            current_job = {
                "title":    parts[0] if len(parts) > 0 else title_meta,
                "company":  parts[1] if len(parts) > 1 else "",
                "duration": parts[2] if len(parts) > 2 else "",
                "bullets":  [],
            }
        elif line.startswith(("-", "•", "*")) and current_job:
            bullet = re.sub(r"^[-•*]\s*", "", line).strip()
            if bullet:
                current_job["bullets"].append(bullet)

    if current_job:
        jobs.append(current_job)
    sections["experience"] = jobs


def _parse_skills(sections: dict, lines: list) -> None:
    """Parses skills section into list of (category, values) tuples."""
    skill_groups = []
    for line in lines:
        # Pattern: **Category:** value1, value2
        match = re.match(r"\**([^*:]+)\**:\s*(.+)", line)
        if match:
            label = match.group(1).strip().rstrip("*")
            value = match.group(2).strip()
            skill_groups.append((label, value))
        elif line.startswith(("-", "•")) and skill_groups:
            # Continuation bullet — append to last group
            extra = re.sub(r"^[-•]\s*", "", line).strip()
            if extra and skill_groups:
                label, val = skill_groups[-1]
                skill_groups[-1] = (label, val + ", " + extra)
    sections["skills"] = skill_groups


def _parse_education(sections: dict, lines: list) -> None:
    """Parses education section."""
    edu_entries = []
    current = None
    for line in lines:
        if not line.startswith(("-", "•", "*")):
            if current:
                edu_entries.append(current)
            parts = [p.strip() for p in line.split("|")]
            current = {
                "institution": parts[0] if parts else line,
                "degree":      parts[1] if len(parts) > 1 else "",
                "year":        parts[2] if len(parts) > 2 else "",
            }
        elif current:
            detail = re.sub(r"^[-•*]\s*", "", line).strip()
            if detail:
                current["degree"] += f" • {detail}"
    if current:
        edu_entries.append(current)
    sections["education"] = edu_entries


def _parse_projects(sections: dict, lines: list) -> None:
    """Parses projects section."""
    projects = []
    current = None
    for line in lines:
        if not line.startswith(("-", "•", "*")):
            if current:
                projects.append(current)
            name_tech = re.sub(r"^#+\s*", "", line).strip()
            parts     = [p.strip() for p in name_tech.split("|")]
            current   = {
                "name":    parts[0],
                "tech":    parts[1] if len(parts) > 1 else "",
                "bullets": [],
            }
        elif current:
            bullet = re.sub(r"^[-•*]\s*", "", line).strip()
            if bullet:
                current["bullets"].append(bullet)
    if current:
        projects.append(current)
    sections["projects"] = projects


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PDF BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def generate_resume_pdf(
    tailored_resume_markdown: str,
    output_path: str,
    user_profile: dict = None,
) -> str:
    """
    Converts the LLM-generated Markdown resume into a professional PDF.

    Args:
        tailored_resume_markdown: The full resume in Markdown format
                                   as generated by the resume_generator node.
        output_path: Full file path where the PDF should be saved.
        user_profile: Original user profile dict (used as fallback
                       for contact info if parsing misses anything).

    Returns:
        The output_path string on success.

    Raises:
        Exception: If PDF generation fails.
    """
    s = _styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="Resume",
        author="AI Job Application Agent",
    )

    story = []
    data  = _parse_resume_sections(tailored_resume_markdown)

    # ── Fallback: use user_profile for contact info ────────────
    if user_profile and not data["name"]:
        personal    = user_profile.get("personal", {})
        data["name"] = personal.get("name", "Candidate")

    if user_profile and not data["contact"]:
        personal = user_profile.get("personal", {})
        data["contact"] = [
            c for c in [
                personal.get("phone", ""),
                personal.get("email", ""),
                personal.get("linkedin", ""),
                personal.get("github", ""),
                personal.get("location", ""),
            ] if c
        ]

    # ── HEADER: Name ───────────────────────────────────────────
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(data["name"], s["name"]))

    # ── HEADER: Contact bar ────────────────────────────────────
    if data["contact"]:
        contact_line = "  |  ".join(data["contact"][:6])
        story.append(Paragraph(_clean(contact_line), s["contact"]))

    story.append(HRFlowable(
        width="100%", thickness=1.2,
        color=ACCENT, spaceAfter=6
    ))

    # ── PROFESSIONAL SUMMARY ───────────────────────────────────
    if data["summary"]:
        _section(story, "Professional Summary", s)
        story.append(Paragraph(_clean(data["summary"]), s["summary"]))

    # ── EDUCATION ──────────────────────────────────────────────
    if data["education"]:
        _section(story, "Education", s)
        for edu in data["education"]:
            # Institution right-aligned with year
            inst_text = _clean(edu["institution"])
            year_text = _clean(edu.get("year", ""))
            if year_text:
                table_data = [[
                    Paragraph(inst_text, s["education_inst"]),
                    Paragraph(year_text, ParagraphStyle(
                        "yr", fontSize=FS_BODY, fontName="Helvetica",
                        textColor=LIGHT_GREY, alignment=TA_RIGHT
                    )),
                ]]
                t = Table(table_data, colWidths=[
                    PAGE_W - MARGIN_LEFT - MARGIN_RIGHT - 30 * mm,
                    28 * mm
                ])
                t.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING",  (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING",   (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
                ]))
                story.append(t)
            else:
                story.append(Paragraph(inst_text, s["education_inst"]))

            if edu.get("degree"):
                story.append(
                    Paragraph(_clean(edu["degree"]), s["education_meta"])
                )

    # ── SKILLS ────────────────────────────────────────────────
    if data["skills"]:
        _section(story, "Skills", s)
        for label, value in data["skills"]:
            story.append(
                Paragraph(f"<b>{_clean(label)}:</b> {_clean(value)}", s["skills_value"])
            )

    # ── PROFESSIONAL EXPERIENCE ────────────────────────────────
    if data["experience"]:
        _section(story, "Professional Experience", s)
        for job in data["experience"]:
            # Title + duration on same line
            title    = _clean(job.get("title", ""))
            company  = _clean(job.get("company", ""))
            duration = _clean(job.get("duration", ""))

            header_left  = f"<b>{title}</b>" + (f" — {company}" if company else "")
            header_right = duration

            table_data = [[
                Paragraph(header_left, s["company_title"]),
                Paragraph(header_right, ParagraphStyle(
                    "dur", fontSize=FS_BODY, fontName="Helvetica-Oblique",
                    textColor=LIGHT_GREY, alignment=TA_RIGHT,
                    spaceBefore=6
                )),
            ]]
            t = Table(table_data, colWidths=[
                PAGE_W - MARGIN_LEFT - MARGIN_RIGHT - 35 * mm,
                33 * mm
            ])
            t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING",   (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
            ]))
            story.append(t)

            for bullet in job.get("bullets", []):
                story.append(
                    Paragraph(f"• {_clean(bullet)}", s["bullet"])
                )

    # ── PROJECTS ──────────────────────────────────────────────
    if data["projects"]:
        _section(story, "Projects", s)
        for project in data["projects"]:
            name = _clean(project.get("name", ""))
            tech = _clean(project.get("tech", ""))
            header = f"<b>{name}</b>"
            if tech:
                header += f"  <font color='#888888' size='8'>| {tech}</font>"
            story.append(Paragraph(header, s["company_title"]))
            for bullet in project.get("bullets", []):
                story.append(
                    Paragraph(f"• {_clean(bullet)}", s["bullet"])
                )

    # ── CERTIFICATIONS ────────────────────────────────────────
    if data["certifications"]:
        _section(story, "Certifications & Courses", s)
        for cert in data["certifications"]:
            story.append(
                Paragraph(f"• {_clean(cert)}", s["bullet"])
            )

    # ── BUILD ─────────────────────────────────────────────────
    doc.build(story)
    return output_path