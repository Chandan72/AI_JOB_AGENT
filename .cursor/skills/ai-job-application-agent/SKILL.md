---
name: ai-job-application-agent
description: >-
  Implements and maintains a LangGraph-based AI job application agent that extracts job details from URLs or raw text, generates tailored resumes, cover letters, and cold emails from a local user profile JSON, and writes Markdown outputs. Use when building, updating, or running the AI Job Application Agent MVP (job extraction, resume tailoring, cover letter, cold email pipeline) in this project.
---

# AI Job Application Agent (MVP)

## Purpose

This skill guides the agent to implement and work with the **AI Job Application Agent — MVP v1.0** described in the product requirements document.  
The agent should use this skill whenever the user wants to:

- Build or modify the LangGraph orchestration for the job application pipeline
- Add or adjust graph nodes (`router`, `job_fetcher`, `job_extractor`, `resume_generator`, `cover_letter_generator`, `cold_email_drafter`, `output_formatter`)
- Run the CLI to process a job description (URL or raw text) and generate:
  - `resume.md`
  - `cover_letter.md`
  - `cold_email.md`

Scope is limited to the MVP features: job extraction from URL/text, tailored resume, cover letter, cold email. Application tracking, ATS autofill, extensions, and other v2 items are out of scope.

---

## High-Level Architecture

Follow this architecture when creating or updating the implementation.

### State Schema (Python)

Represent the agent state as a Pydantic v2 model:

```python
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    job_input: str
    input_type: Literal["url", "text"]
    user_profile: Dict[str, Any]
    raw_job_content: str
    job_details: Dict[str, Any]
    tailored_resume: str
    cover_letter: str
    cold_email: str
    error: Optional[str] = Field(default=None)
    current_step: str
```

Use this state (or a close equivalent) as the LangGraph state object. If the framework requires a different shape (e.g. mapping type), adapt minimally while preserving all fields.

### Graph Flow

The pipeline should follow this flow:

```text
User Input (URL or JD Text)
        │
        ▼
  [router]
    ├─ "url"  → [job_fetcher]
    └─ "text" → (skip fetcher, use raw text)
        │
        ▼
  [job_extractor]
        │
        ▼
  [resume_generator]
        │
        ▼
  [cover_letter_generator]
        │
        ▼
  [cold_email_drafter]
        │
        ▼
  [output_formatter] → writes Markdown files
```

Use **LangGraph 0.2+** conventions for nodes and routing.

---

## Implementation Guidelines

### Project Layout

Prefer this structure inside the project:

```text
ai_job_agent/
  ├─ __init__.py
  ├─ config.py
  ├─ state.py
  ├─ nodes/
  │   ├─ router.py
  │   ├─ job_fetcher.py
  │   ├─ job_extractor.py
  │   ├─ resume_generator.py
  │   ├─ cover_letter_generator.py
  │   ├─ cold_email_drafter.py
  │   └─ output_formatter.py
  ├─ graph.py
  ├─ cli.py
  └─ prompts/
      ├─ job_extractor_prompt.md
      ├─ resume_prompt.md
      ├─ cover_letter_prompt.md
      └─ cold_email_prompt.md
profile.json
outputs/
  ├─ resume.md
  ├─ cover_letter.md
  └─ cold_email.md
```

If an alternative layout already exists, adapt these instructions to that layout rather than forcing a rewrite.

### Tech Stack (MVP)

When adding dependencies or wiring integrations, follow this stack:

- **Orchestration:** LangGraph 0.2+
- **LLMs:**  
  - Primary: Anthropic Claude Sonnet via `langchain-anthropic`  
  - Fallback: OpenAI GPT-4o via `langchain-openai`
- **Web scraping:** `requests` + `beautifulsoup4`
- **Structured parsing:** Pydantic v2
- **CLI:** `Typer` + `Rich`
- **Config:** `python-dotenv` for API keys and environment config
- **Output:** Markdown files under `./outputs/`

Document new dependencies in `pyproject.toml` or `requirements.txt` (whichever the project uses).

---

## Node Specifications (What Each Node Must Do)

Use these responsibilities and failure modes when implementing or updating nodes.

### 1. `router`

- **Input:** `job_input` (string)
- **Logic:**
  - If `job_input` matches an `http://` or `https://` URL pattern, set `input_type = "url"`.
  - Otherwise, set `input_type = "text"`.
  - On ambiguous cases, default to `"text"`.
- **Output:**
  - Update `state.input_type`.
  - Set `state.current_step = "router"`.

### 2. `job_fetcher`

- **Trigger:** Only run if `state.input_type == "url"`.
- **Logic:**
  - Use `requests` to fetch the page.
  - Use `BeautifulSoup` to extract job description text, preferring:
    - `<article>`
    - `<main>`
    - elements with `.job-description` or similar selectors
  - If these fail, fall back to full page text.
- **Output:**
  - Set `state.raw_job_content` to the extracted text.
  - Update `state.current_step = "job_fetcher"`.
- **Failure mode:**
  - On error (network, parsing), set `state.error` but **do not** abort the pipeline.
  - As a fallback, set `state.raw_job_content = state.job_input` (the URL string) so downstream nodes can still run.

### 3. `job_extractor`

- **Input:** `state.raw_job_content` (if URL) or `state.job_input` (if raw text).
- **Logic:**
  - Call the LLM using a **structured output** schema (Pydantic v2 or LangChain equivalent).
  - Extract at least:
    - `company_name`
    - `job_title`
    - `location`
    - `job_type`
    - `required_skills`
    - `preferred_skills`
    - `responsibilities`
    - `requirements`
    - `salary_range`
    - `about_company`
    - `recruiter_signals` (useful hints/hooks for outreach)
- **Output:**
  - Set `state.job_details` to a structured dict.
  - Update `state.current_step = "job_extractor"`.

### 4. `resume_generator`

- **Input:** `state.job_details`, `state.user_profile`.
- **Logic:**
  - Use an LLM prompt that **rewrites** the user’s existing bullets and sections to match the job description language.
  - **No fabrication is allowed**:
    - Do not add experiences, companies, roles, or skills that are not present in `user_profile`.
    - You may reorder, merge, split, and rephrase existing bullets.
  - Map each resume change conceptually back to one or more `user_profile` fields to maintain traceability (even if not explicitly surfaced to the user).
- **Output:**
  - Set `state.tailored_resume` as a Markdown string.
  - Update `state.current_step = "resume_generator"`.

### 5. `cover_letter_generator`

- **Input:** `state.job_details`, `state.user_profile`.
- **Logic:**
  - Generate a **3-paragraph cover letter**:
    1. Company-specific hook that references `company_name`, role, and one strong alignment signal from `job_details`.
    2. Two best matching experiences from `user_profile.experience` and/or `projects`.
    3. Clear call to action (e.g. interest in speaking, link to portfolio).
  - Output must be Markdown.
- **Output:**
  - Set `state.cover_letter`.
  - Update `state.current_step = "cover_letter_generator"`.

### 6. `cold_email_drafter`

- **Input:** `state.job_details`, `state.user_profile`.
- **Logic:**
  - Generate a short cold email suitable for **recruiters or hiring managers**:
    - 5–7 lines of body text.
    - Include a concise subject line.
    - Reference role, company, and 1–2 key fit points.
    - Tone: professional, confident, concise.
  - Output must be Markdown.
- **Output:**
  - Set `state.cold_email`.
  - Update `state.current_step = "cold_email_drafter"`.

### 7. `output_formatter`

- **Input:** `state.tailored_resume`, `state.cover_letter`, `state.cold_email`, `state.job_details`, `state.error`.
- **Logic:**
  - Ensure `./outputs/` exists (create if needed).
  - Write:
    - `outputs/resume.md`
    - `outputs/cover_letter.md`
    - `outputs/cold_email.md`
  - Optionally, print a Rich-formatted summary to the console:
    - Job title, company, location.
    - Where files were written.
    - Any non-fatal errors encountered (e.g. scraping fallbacks).
- **Output:**
  - Files written successfully.
  - Update `state.current_step = "output_formatter"`.

---

## User Profile Handling

### Expected Schema

The agent should expect the user profile JSON to follow this structure:

```json
{
  "personal": {
    "name": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "linkedin": "string",
    "github": "string",
    "portfolio": "string"
  },
  "summary": "string",
  "experience": [
    {
      "company": "string",
      "title": "string",
      "duration": "string",
      "bullets": ["string"]
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "year": "string",
      "gpa": "string"
    }
  ],
  "skills": {
    "technical": ["string"],
    "soft": ["string"],
    "tools": ["string"]
  },
  "projects": [
    {
      "name": "string",
      "description": "string",
      "tech_stack": ["string"],
      "impact": "string"
    }
  ],
  "certifications": ["string"],
  "achievements": ["string"]
}
```

Store this as `profile.json` at the project root (or a clearly documented alternative). When the user asks to update their profile, modify this file while preserving the schema.

### No-Fabrication Rule

The resume generator must **never**:

- Invent new jobs, titles, or employers.
- Add skills or tools not present in `skills` or demonstrably implied by existing bullets.
- Inflate seniority or impact beyond what is clearly supported.

It may:

- Re-order bullets to better match the job description.
- Rephrase content using JD keywords where accurate.
- Merge, split, or slightly expand bullets to clarify impact, as long as it stays truthful.

---

## CLI Workflow

Implement a CLI using `Typer` (and `Rich` for nice output) with a main entrypoint like:

```bash
python -m ai_job_agent.cli run --job-input "<url-or-text>" --profile-path "profile.json"
```

Recommended CLI design:

- **Command:** `run`
- **Options:**
  - `--job-input TEXT` (required): URL or raw job description text.
  - `--profile-path PATH` (optional, default `"profile.json"`).
  - `--model-provider [anthropic|openai]` (optional) to choose primary model.
  - `--output-dir PATH` (optional, default `"outputs"`).
- **Behavior:**
  - Load env config (API keys) via `python-dotenv` if present.
  - Load and validate user profile JSON.
  - Construct and run the LangGraph app end-to-end.
  - Report where outputs were written and any non-fatal errors.

---

## Non-Functional Requirements to Enforce

When implementing or modifying the system, keep these constraints in mind:

- **No fabrication:**  
  - Resume and cover letter must not invent experience or skills.
- **Graceful degradation:**  
  - If scraping fails, continue using `job_input` as raw JD content.
- **Transparency:**  
  - Structure prompts so that changes can be traced back to `user_profile` fields.
- **Privacy:**  
  - Assume that only LLM API calls leave the machine. Avoid logging sensitive user data unnecessarily.
- **Speed:**  
  - Aim for end-to-end runtime under 60 seconds for typical JDs.

If trade-offs are required (e.g. higher temperature vs accuracy), favor **accuracy and faithfulness** over creativity.

---

## Usage Examples

The agent should encourage workflows like:

- **From URL:**
  - User provides a job posting URL and asks to generate application materials.
  - Agent updates or creates `profile.json` if needed.
  - Agent runs the CLI or underlying graph to produce `outputs/*.md`.

- **From raw JD text:**
  - User pastes a job description.
  - Agent sets `input_type = "text"` via `router`.
  - Same pipeline runs, skipping `job_fetcher`.

---

## When Not to Use This Skill

Do **not** apply this skill for:

- General resume writing without a specific job description.
- Interview prep, offer negotiation, application tracking, or ATS autofill.
- Non-job-related email generation.

For those tasks, use generic capabilities or other dedicated skills instead.

---

## Checklist Before Considering the MVP “Done”

When the user asks to complete or verify the MVP, confirm:

- [ ] LangGraph pipeline is wired with all nodes in the correct order.
- [ ] Job details extraction achieves reasonably structured outputs (`job_details` shape).
- [ ] `profile.json` exists and matches the schema.
- [ ] CLI command runs end-to-end from job input to `outputs/*.md`.
- [ ] Outputs sound like the candidate (user-reported “sounds like me” is high).
- [ ] System respects the no-fabrication rule and degrades gracefully when scraping fails.

