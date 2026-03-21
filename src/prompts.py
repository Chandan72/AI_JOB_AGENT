from langchain_core.prompts import ChatPromptTemplate


# ── Job Extractor ──────────────────────────────────────────────
JOB_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an expert job posting analyst. Extract structured information
from job postings with precision. Return ONLY valid JSON matching the schema.
If a field is not present in the posting, use an empty string or empty list.
Do not infer or hallucinate information not explicitly stated.""",
        ),
        (
            "human",
            """Extract all available information from this job posting into JSON.

Job Posting Content:
─────────────────────
{raw_job_content}
─────────────────────

Return a single JSON object with these exact keys:
{{
  "company_name": "string",
  "job_title": "string",
  "job_url": "string",
  "location": "string",
  "job_type": "string",
  "seniority_level": "string — Junior / Mid / Senior / Staff / Lead / Director / VP",
  "industry": "string",
  "salary_range": "string",
  "about_company": "string — 2-3 sentences max",
  "team_info": "string",
  "required_skills": ["list of must-have skills"],
  "preferred_skills": ["list of nice-to-have skills"],
  "tech_stack": ["specific technologies and tools mentioned"],
  "responsibilities": ["list of key responsibilities"],
  "requirements": ["list of explicit requirements"],
  "recruiter_name": "string",
  "hiring_manager_name": "string",
  "application_email": "string"
}}

Return ONLY the JSON object. No markdown fences. No explanation.""",
        ),
    ]
)


# ── Resume Generator ───────────────────────────────────────────
RESUME_GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an expert resume writer with 10 years of experience helping
candidates land roles at top companies.

CRITICAL CONSTRAINT: You may ONLY use information explicitly provided in the
candidate profile. You MUST NOT add, invent, or imply any skill, experience,
or achievement not present in the profile. Reframe real experience — never fabricate.

Your goal is to rewrite the candidate's existing experience in language that
resonates with this specific job description.""",
        ),
        (
            "human",
            """Create a tailored resume for this candidate applying to this role.

━━━━━━━━━━━━━━━━━━━━━
CANDIDATE PROFILE
━━━━━━━━━━━━━━━━━━━━━
{user_profile}

━━━━━━━━━━━━━━━━━━━━━
TARGET JOB DETAILS
━━━━━━━━━━━━━━━━━━━━━
Company: {company_name}
Role: {job_title}
Company Context: {company_context}
Required Skills: {required_skills}
Preferred Skills: {preferred_skills}
Key Responsibilities: {responsibilities}
Key Requirements: {requirements}
Tech Stack: {tech_stack}
Seniority: {seniority_level}

━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━
1. Open with a 2-line professional summary mirroring this job's language
2. Rewrite experience bullets to emphasise skills relevant to this role
3. Quantify impact wherever the profile provides numbers — never invent numbers
4. Move the most relevant experience and skills to the top
5. Mirror keywords from the job description naturally — not keyword-stuffed
6. Keep each bullet under 2 lines: Action verb + what you did + measurable result

Format in clean Markdown with these exact section headers:
# [Candidate Name]
## Contact
## Professional Summary
## Experience
## Skills
## Education
## Projects (if applicable)
## Certifications (if applicable)

At the bottom add:
## Tailoring Notes
- List 3-5 specific changes made and why
""",
        ),
    ]
)


# ── Cover Letter Generator ─────────────────────────────────────
COVER_LETTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a senior career coach who writes cover letters that
actually get read. Your letters are direct, specific, and confident.
You never start with 'I am writing to express my interest in...'

Always use the Hook-Proof-Close framework:
  Paragraph 1 (Hook): Something specific about the company showing genuine research.
  Paragraph 2 (Proof): Candidate's 2 most relevant experiences with outcomes.
  Paragraph 3 (Close): Direct confident ask with clear next step.""",
        ),
        (
            "human",
            """Write a targeted cover letter for this application.

━━━━━━━━━━━━━━━━━━━━━
CANDIDATE PROFILE
━━━━━━━━━━━━━━━━━━━━━
{user_profile}

━━━━━━━━━━━━━━━━━━━━━
TARGET JOB DETAILS
━━━━━━━━━━━━━━━━━━━━━
Company: {company_name}
Role: {job_title}
About Company: {about_company}
Team Info: {team_info}
Company Intelligence: {company_intelligence}
Suggested Hook: {cover_letter_hook}
Required Skills: {required_skills}
Key Responsibilities: {responsibilities}
Seniority Level: {seniority_level}
Hiring Manager: {hiring_manager_name}

━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━
1. Opening hook must reference something specific to {company_name}
2. Do not start with 'I am applying for...'
3. Keep total length to 3 tight paragraphs — under 300 words
4. Match the candidate's voice — professional but human
5. End with a specific call to action
6. ONLY use achievements from the candidate profile

Format as clean Markdown:
# Cover Letter — {job_title} at {company_name}

[Date]

Dear Hiring Team,

[Body — 3 paragraphs]

[Sign-off]
[Candidate Name]
""",
        ),
    ]
)


# ── Cold Email Drafter ─────────────────────────────────────────
# ── Cold Email Drafter (Single Version) ───────────────────────
COLD_EMAIL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert cold email writer.
You write one focused, targeted cold email that gets replies.

Your emails are:
  - Short: under 100 words in the body
  - Specific: reference something real about the company
  - Valuable: lead with what the candidate brings
  - Human: sounds like a real person wrote it
  - Clean: NO placeholder text like [Name] or [Company]
    Use real names from the data. If unknown use 'Hi there,'

Never use square bracket placeholders of any kind."""),

    ("human", """Write ONE cold email for this candidate.

━━━━━━━━━━━━━━━━━━━━━
TARGET
━━━━━━━━━━━━━━━━━━━━━
Sending to: {target_type}
Name: {target_name}
Company: {company_name}
Role: {job_title}

━━━━━━━━━━━━━━━━━━━━━
CANDIDATE PROFILE
━━━━━━━━━━━━━━━━━━━━━
{user_profile}

━━━━━━━━━━━━━━━━━━━━━
COMPANY INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━
{company_intelligence}

━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━
1. Subject line must be specific and compelling
2. Opening line references something real about {company_name}
3. One sentence on what the candidate brings to THIS role
4. One specific proof point with a number from their profile
5. Simple ask — 15 minute call or portfolio link
6. Sign off with candidate first name only
7. Under 100 words in the body
8. NO placeholders — use real names or 'Hi there,'

Format exactly like this:

**Subject:** [your subject line]

[greeting],

[body — 3-4 sentences max]

[sign-off],
[first name]""")
])
# ── Company Research RAG ───────────────────────────────────────
COMPANY_RESEARCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     """You are a senior business analyst and career strategist.
Your job is to analyse raw company research and extract intelligence
that helps a job candidate make a stronger, more specific application.

You focus on signals that are directly useful for:
1. Writing a specific cover letter hook
2. Framing the candidate's experience against company challenges
3. Writing a cold email that shows genuine research

Be precise. Be factual. Only include what is actually present
in the research content. Never invent facts about a company."""),

    ("human", """Analyse this research about {company_name} and extract
structured intelligence for a job candidate applying for {job_title}.

━━━━━━━━━━━━━━━━━━━━━
RAW RESEARCH CONTENT
━━━━━━━━━━━━━━━━━━━━━
{raw_research}

━━━━━━━━━━━━━━━━━━━━━
EXTRACT INTO JSON
━━━━━━━━━━━━━━━━━━━━━
Return a single JSON object with these exact keys:

{{
  "company_summary": "2-3 sentence description of what the company does and where it is in its journey",
  "recent_news": ["list of 2-3 specific recent developments, launches, or announcements"],
  "growth_signals": "evidence of growth stage — hiring surge, funding, expansion, new markets",
  "challenges": ["list of 1-2 challenges the company is visibly facing or solving"],
  "culture_signals": ["list of 2-3 cultural values or working style signals from reviews or content"],
  "cover_letter_hook": "one specific, concrete opening sentence for a cover letter that references something real and recent about this company — NOT generic praise",
  "cold_email_context": "one sentence of company context that makes a cold email feel researched and specific",
  "relevance_to_role": "how the company's current situation makes this specific role important right now"
}}

Return ONLY the JSON. No markdown fences. No explanation.""")
])

# ── Email Regeneration (Human Feedback) ───────────────────────
# ── Email Regeneration (Human Feedback) ───────────────────────
EMAIL_REGENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert cold email writer improving 
an existing cold email based on specific human feedback.

CRITICAL RULES — NEVER BREAK THESE:
1. ALWAYS output BOTH Version A and Version B in full
2. NEVER remove the email body — only modify what feedback asks
3. NEVER shrink the email to just a signature or contact info
4. ONLY change the specific things mentioned in the feedback
5. Keep everything else EXACTLY as it was
6. Always preserve the full Markdown structure:
   - ## Version A header
   - **To:** line
   - **Subject:** line
   - Full email body paragraphs
   - Sign-off with candidate name
   - ## Version B header (same structure)
   - ## Usage Notes section

If feedback says "change X to Y" — change ONLY that.
If feedback says "make it more casual" — rewrite tone only.
If feedback says "make it shorter" — trim but keep full structure.
NEVER output just a signature. NEVER output just contact info."""),

    ("human", """Improve this cold email based on the feedback.

━━━━━━━━━━━━━━━━━━━━━
ORIGINAL EMAIL (keep this full structure)
━━━━━━━━━━━━━━━━━━━━━
{current_email}

━━━━━━━━━━━━━━━━━━━━━
FEEDBACK TO APPLY
━━━━━━━━━━━━━━━━━━━━━
{feedback}

━━━━━━━━━━━━━━━━━━━━━
CANDIDATE PROFILE
━━━━━━━━━━━━━━━━━━━━━
{user_profile}

━━━━━━━━━━━━━━━━━━━━━
COMPANY CONTEXT
━━━━━━━━━━━━━━━━━━━━━
{company_context}

━━━━━━━━━━━━━━━━━━━━━
OUTPUT REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━
Output the COMPLETE improved email with this exact structure:

# Cold Outreach Emails — [Role] at [Company]

## Version A — To Recruiter
**To:** [recruiter name or generic]
**Subject:** [subject line]

[Full email body — minimum 3 sentences]

[Sign-off]
[Candidate name]

---

## Version B — To Hiring Manager
**To:** [hiring manager name or generic]
**Subject:** [subject line]

[Full email body — minimum 3 sentences]

[Sign-off]
[Candidate name]

---

## Usage Notes
- Send Version A first via LinkedIn or email
- Wait 5 business days before sending Version B
- Never send both on the same day

Apply ONLY what the feedback asks. Keep everything else identical.""")
])