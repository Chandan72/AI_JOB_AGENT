from langchain_core.prompts import ChatPromptTemplate
from langsmith import Client
import os
client=Client(api_url="https://api.smith.langchain.com", api_key=os.getenv("LANGSMITH_API_KEY"))
JOB_EXTRACTION_PROMPT=client.pull_prompt("job_extraction",include_model=False)
RESUME_GENERATION_PROMPT=client.pull_prompt("resume_generator", include_model=False)
COVER_LETTER_PROMPT=client.pull_prompt("cover_letter", include_model=False)
COLD_EMAIL_PROMPT=client.pull_prompt("cold_mail", include_model=False)

COMPANY_RESEARCH_PROMPT=client.pull_prompt("company_research", include_model=False)
EMAIL_REGENERATION_PROMPT=client.pull_prompt("email_regeneration", include_model=False)
ATS_EXPERT_PROMPT=client.pull_prompt("ats_expert", include_model=False)


# ── Resume Generator ───────────────────────────────────────────




# ── Cover Letter Generator ─────────────────────────────────────


# ── Cold Email Drafter ─────────────────────────────────────────
# ── Cold Email Drafter (Single Version) ───────────────────────

# ── Company Research RAG ───────────────────────────────────────

# ── Email Regeneration (Human Feedback) ───────────────────────
# ── Email Regeneration (Human Feedback) ───────────────────────


# ── ATS Expert ─────────────────────────────────────────────────
