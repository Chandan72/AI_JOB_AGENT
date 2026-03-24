"""
config.py — LLM Configuration with Auto-Fallback
"""

import os
import time
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


class Config:
    LLM_PROVIDER           = os.getenv("LLM_PROVIDER", "openrouter")
    ANTHROPIC_API_KEY      = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY         = os.getenv("OPENAI_API_KEY", "")
    OPENROUTER_API_KEY     = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL    = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL_FAST  = os.getenv("OPENROUTER_MODEL_FAST",  "stepfun/step-3.5-flash:free")
    OPENROUTER_MODEL_SMART = os.getenv("OPENROUTER_MODEL_SMART", "nvidia/nemotron-3-super-120b-a12b:free")
    TAVILY_API_KEY         = os.getenv("TAVILY_API_KEY", "")
    GMAIL_SENDER_EMAIL     = os.getenv("GMAIL_SENDER_EMAIL", "")
    GMAIL_APP_PASSWORD     = os.getenv("GMAIL_APP_PASSWORD", "")
    OUTPUT_DIR             = os.getenv("OUTPUT_DIR", "./outputs")
    REQUEST_TIMEOUT        = int(os.getenv("REQUEST_TIMEOUT", "15"))
    USER_AGENT             = os.getenv("USER_AGENT", "Mozilla/5.0")


# Tasks that need accuracy → FAST model first
FAST_TASKS  = {"extraction", "analysis", "routing"}

# Tasks that need quality → SMART model first
SMART_TASKS = {"generation", "research", "refinement"}

# Tried in order when both primary models fail
FALLBACK_MODELS = [
    "arcee-ai/trinity-mini:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "google/gemma-3n-e4b-it:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "z-ai/glm-4.5-air:free",
    "arcee-ai/trinity-large-preview:free",
    "qwen/qwen3-4b:free",
]


def _is_rate_limit(error: Exception) -> bool:
    msg = str(error).lower()
    return "429" in msg or "rate" in msg or "too many" in msg


def _try_model(model: str, temperature: float) -> BaseChatModel | None:
    """
    Tries one model up to 3 times with exponential backoff.
    Returns working LLM or None if unavailable.
    """
    from langchain_openai import ChatOpenAI
    wait = 2

    for attempt in range(3):
        try:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=Config.OPENROUTER_API_KEY,
                base_url=Config.OPENROUTER_BASE_URL,
                default_headers={
                    "HTTP-Referer": "https://github.com/Chandan72/ai-job-agent",
                    "X-Title": "AI Job Agent",
                },
            )
            llm.invoke("hi", max_tokens=1)  # quick test
            return llm

        except Exception as e:
            if "404" in str(e):
                return None             # model not found — skip
            if _is_rate_limit(e) and attempt < 2:
                time.sleep(wait)        # wait then retry
                wait *= 2               # 2s → 4s → give up
            else:
                return None

    return None


def get_llm_for_task(task: str, temperature: float = 0.0) -> BaseChatModel:
    """
    Returns a working LLM for the given task.

    Fast tasks  (extraction, analysis) → FAST model first
    Smart tasks (generation, research) → SMART model first
    If primary fails → tries the other primary → then fallbacks

    Works for Anthropic and OpenAI too — task param is ignored there.
    """

    # ── Anthropic ──────────────────────────────────────────────
    if Config.LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            temperature=temperature,
            anthropic_api_key=Config.ANTHROPIC_API_KEY,
        )

    # ── OpenAI ─────────────────────────────────────────────────
    elif Config.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o",
            temperature=temperature,
            openai_api_key=Config.OPENAI_API_KEY,
        )

    # ── OpenRouter — fast/smart + fallbacks ────────────────────
    elif Config.LLM_PROVIDER == "openrouter":

        # Order the two primary models by task type
        if task in FAST_TASKS:
            primaries = [Config.OPENROUTER_MODEL_FAST,
                         Config.OPENROUTER_MODEL_SMART]
        else:
            primaries = [Config.OPENROUTER_MODEL_SMART,
                         Config.OPENROUTER_MODEL_FAST]

        # Full list: primaries first, then fallbacks (no duplicates)
        models = primaries + [
            m for m in FALLBACK_MODELS if m not in primaries
        ]

        for model in models:
            llm = _try_model(model, temperature)
            if llm is not None:
                if model not in primaries:
                    print(f"   ⚡ Fallback model: {model}")
                return llm

        raise RuntimeError(
            "All OpenRouter models are rate limited.\n"
            "Wait 1-2 minutes and try again."
        )

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {Config.LLM_PROVIDER}")


def get_llm(temperature: float = 0.3) -> BaseChatModel:
    """Backward compatible wrapper — existing code keeps working."""
    return get_llm_for_task("generation", temperature=temperature)