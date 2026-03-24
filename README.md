
# 🎯 AI Job Application Agent

> **A fully autonomous job hunting and application system built with
> LangGraph + LangChain + Claude.**
>
> Turns a 3-5 hour manual job application into a 47-second
> automated pipeline. 230x leverage.

---

## The Problem I Chose to Solve

The global job market has a broken, dehumanising system.
A typical job seeker in 2025-2026:
- Spends 3-5 hours per application on research and writing
- Applies to 50-200 jobs before getting one offer
- Fills the same form fields hundreds of times
- Gets ghosted 80% of the time with zero feedback
- Has no idea why they are being rejected

This is not a small inconvenience. It is a systemic failure
that affects hundreds of millions of people every year.

**Why this problem?** Because it is personal, massive in scale,
and has a clear AI-first solution. Every step of the process —
research, writing, tailoring, tracking, sending — is automatable
with current LLM capabilities. The only reason it had not been
solved is that nobody built the full end-to-end pipeline.

---

## What I Built

### Pipeline 1 — Application Agent (10 nodes)
```
URL/JD Input
  → router
  → job_fetcher (web scraper)
  → job_extractor (structured LLM extraction)
  → company_researcher (RAG via Tavily)
  → ATS_improver
  → cover_letter_generator (Hook-Proof-Close framework)
  → email_intent_selector (human choice in UI)
  → cold_email_drafter (single targeted email)
  → human_feedback_loop (UI-based refinement)
  → gmail_sender (SMTP delivery)
  → pdf_resume_generator (ReportLab PDF)- remove for now
  → output_formatter (5 files saved)
```

### Pipeline 2 — Job Hunter (7 nodes, runs daily at 10 AM)
```
Profile (resume PDF)
  → profile_loader (PyMuPDF + LLM extraction)
  → job_scraper (Wellfound + YC Jobs via Tavily)
  → deduplicator (SQLite memory, 7-day window)
  → keyword_filter (fast pre-filter)
  → semantic_ranker (sentence-transformers, 384-dim)
  → digest_generator (HTML email)
  → email_sender (Gmail SMTP digest)
```

---

## Architecture Decisions

**Why LangGraph over plain function calls?**
State management. When a pipeline has 10 nodes and any node
can fail, you need explicit state propagation, error routing,
and conditional edges. LangGraph makes the pipeline structure
a first-class artifact — visible, debuggable, extensible.

**Why separate job hunter and application pipelines?**
Different trigger patterns. The hunter runs on a schedule
autonomously. The application pipeline runs on human demand
with human-in-the-loop checkpoints. Combining them would
violate single-responsibility at the pipeline level.

**Why RAG for company research?**
Cover letters that reference specific company news get 3x
more responses than generic ones. The RAG node turns a
generic "I'm excited about your mission" into "I noticed
your recent expansion into stablecoin infrastructure —
that's exactly the problem space I worked on at..."

**Why semantic matching over keyword matching?**
"ML Engineer" and "Machine Learning Developer" mean the
same thing. Keyword matching misses them. Cosine similarity
on sentence-transformer embeddings captures meaning, not
just words. This is how candidates find roles they would
never have searched for.

---

## Performance Score: 7,340 / 10,000

See [PERFORMANCE_METRICS.md](PERFORMANCE_METRICS.md) for
full methodology.

Summary: 90% task completion, 85% job hunter precision,
230x speed improvement, 90% anti-hallucination accuracy.

---

## Benchmark vs Default Cursor + Claude

See [BENCHMARK.md](BENCHMARK.md) for full comparison.

Summary: Our agent adds job discovery, semantic matching,
scheduled autonomy, PDF generation, and email sending —
capabilities that do not exist in a default Cursor session.

---

## Setup

### Prerequisites
- Python 3.11+
- Anthropic API key(you can use open source also)
- Tavily API key (free tier: 1000 searches/month)
- Gmail App Password (2FA must be enabled)

### Installation
```bash
git clone https://github.com/YOUR_USERNAME/ai-job-agent
cd ai-job-agent
python -m venv .venv
 .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

### Run
```bash
# Full web UI (recommended)
streamlit python app.py

# CLI pipeline
python main.py --url "https://wellfound.com/jobs/..."

# Job hunter only
python hunter_main.py run-now
```

---

## Project Structure
```
ai-job-agent/
├── src/
│   ├── state.py          # LangGraph AgentState
│   ├── config.py         # LLM factory (Anthropic/OpenAI)
│   ├── tools.py          # Web scraper
│   ├── prompts.py        # All LLM prompts
│   ├── nodes.py          # All 10 pipeline nodes
│   ├── graph.py          # Graph assembly
│   ├── email_sender.py   # Gmail SMTP
│   └── pdf_generator.py  # ReportLab PDF
├── job_hunter/
│   ├── state.py          # Hunter AgentState
│   ├── profile_parser.py # PDF → structured profile
│   ├── job_scraper.py    # Multi-platform scraper
│   ├── matcher.py        # Semantic ranking
│   ├── tracker.py        # SQLite deduplication
│   ├── digest_generator.py # HTML email
│   └── graph.py          # Hunter graph
├── api/                  # FastAPI backend
├── ui/                   # HTML frontend
├── streamlit_app.py      # Streamlit UI
├── hunter_main.py        # Job hunter CLI
├── main.py               # Application CLI
├── .cursorrules          # Cursor configuration
├── .env.example          # Environment template
├── PERFORMANCE_METRICS.md
└── BENCHMARK.md
```

---

## What I Would Build Next

1. **ATS form autofill** — Browser automation agent using
   Playwright to fill Workday/Greenhouse forms automatically
2. **Application outcome learning** — When user marks a job
   as "rejected" or "offer received", the system learns which
   resume variants and cover letter hooks actually work
3. **Voice interview prep** — Real-time mock interviews using
   Whisper + ElevenLabs with company-specific question databases
4. **Offer negotiation coach** — Compensation benchmarking
   from H1B data + Levels.fyi with negotiation email scripts

---

## Why This Demonstrates FDE/APO Capability

An FDE does not wait for perfect specs. They identify the
highest-leverage problem, define clear priorities, and ship.

I identified that job hunting is a broken, 3-5 hour manual
process. I defined the priority: eliminate every manually
repetitive step first (form filling → resume tailoring →
cover letter → cold email). I built a working system with
230x speed improvement in one session.

That is priority definition ability. That is AI leverage.
That is what this role requires.

---

## Author

Chandan  | IIT Kharagpur
chandan875792@gmail.com
github.com/Chandan72
linkedin.com/in/chandan-kumar-3a0396200
