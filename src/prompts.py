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
COLD_EMAIL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an expert in professional outreach. You write cold emails
that get replies. Your emails are:
  - Short: under 100 words in the body
  - Specific: one concrete reason for reaching out to THIS person
  - Valuable: signals what the candidate brings, not just what they want
  - Human: sounds like a real person wrote it, not a template

Write TWO versions:
  Version A: To the recruiter
  Version B: To the hiring manager""",
        ),
        (
            "human",
            """Draft cold outreach emails for this candidate.

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
Required Skills: {required_skills}
Recruiter: {recruiter_name}
Hiring Manager: {hiring_manager_name}
Application Email: {application_email}

━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━
1. Subject line must be specific — not just 'Following up on [role]'
2. Open with one sentence showing context awareness
3. One sentence on what the candidate brings relevant to this role
4. One specific proof point — a number or achievement from their profile
5. Simple ask: 15-minute call or share portfolio link
6. Sign off with first name only

Format as Markdown:

# Cold Outreach Emails — {job_title} at {company_name}

## Version A — To Recruiter
**To:** {recruiter_name}
**Subject:** [subject line]

[email body — under 100 words]

---

## Version B — To Hiring Manager
**To:** {hiring_manager_name}
**Subject:** [subject line]

[email body — under 100 words]

---

## Usage Notes
- Send Version A first via LinkedIn or email
- Wait 5 business days before sending Version B
- Never send both on the same day
""",
        ),
    ]
)
from langchain_core.prompts import ChatPromptTemplate


# ── Job Extractor ──────────────────────────────────────────────
JOB_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert job posting analyst. Extract structured information
from job postings with precision. Return ONLY valid JSON matching the schema.
If a field is not present in the posting, use an empty string or empty list.
Do not infer or hallucinate information not explicitly stated."""),

    ("human", """Extract all available information from this job posting into JSON.

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

Return ONLY the JSON object. No markdown fences. No explanation.""")
])


# ── Resume Generator ───────────────────────────────────────────
RESUME_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert resume writer with 10 years of experience helping
candidates land roles at top companies.

CRITICAL CONSTRAINT: You may ONLY use information explicitly provided in the
candidate profile. You MUST NOT add, invent, or imply any skill, experience,
or achievement not present in the profile. Reframe real experience — never fabricate.

Your goal is to rewrite the candidate's existing experience in language that
resonates with this specific job description."""),

    ("human", """Create a tailored resume for this candidate applying to this role.

━━━━━━━━━━━━━━━━━━━━━
CANDIDATE PROFILE
━━━━━━━━━━━━━━━━━━━━━
{user_profile}

━━━━━━━━━━━━━━━━━━━━━
TARGET JOB DETAILS
━━━━━━━━━━━━━━━━━━━━━
Company: {company_name}
Role: {job_title}
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
""")
])


# ── Cover Letter Generator ─────────────────────────────────────
COVER_LETTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a senior career coach who writes cover letters that
actually get read. Your letters are direct, specific, and confident.
You never start with 'I am writing to express my interest in...'

Always use the Hook-Proof-Close framework:
  Paragraph 1 (Hook): Something specific about the company showing genuine research.
  Paragraph 2 (Proof): Candidate's 2 most relevant experiences with outcomes.
  Paragraph 3 (Close): Direct confident ask with clear next step."""),

    ("human", """Write a targeted cover letter for this application.

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
""")
])


# ── Cold Email Drafter ─────────────────────────────────────────
COLD_EMAIL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert in professional outreach. You write cold emails
that get replies. Your emails are:
  - Short: under 100 words in the body
  - Specific: one concrete reason for reaching out to THIS person
  - Valuable: signals what the candidate brings, not just what they want
  - Human: sounds like a real person wrote it, not a template

Write TWO versions:
  Version A: To the recruiter
  Version B: To the hiring manager"""),

    ("human", """Draft cold outreach emails for this candidate.

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
Required Skills: {required_skills}
Recruiter: {recruiter_name}
Hiring Manager: {hiring_manager_name}
Application Email: {application_email}

━━━━━━━━━━━━━━━━━━━━━
INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━
1. Subject line must be specific — not just 'Following up on [role]'
2. Open with one sentence showing context awareness
3. One sentence on what the candidate brings relevant to this role
4. One specific proof point — a number or achievement from their profile
5. Simple ask: 15-minute call or share portfolio link
6. Sign off with first name only

Format as Markdown:

# Cold Outreach Emails — {job_title} at {company_name}

## Version A — To Recruiter
**To:** {recruiter_name}
**Subject:** [subject line]

[email body — under 100 words]

---

## Version B — To Hiring Manager
**To:** {hiring_manager_name}
**Subject:** [subject line]

[email body — under 100 words]

---

## Usage Notes
- Send Version A first via LinkedIn or email
- Wait 5 business days before sending Version B
- Never send both on the same day
""")
])