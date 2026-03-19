import os

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


class Config:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./outputs")
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
    )
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")  # ← NEW
    OPENROUTER_BASE_URL: str = os.getenv(                          # ← NEW
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    @classmethod
    def validate(cls) -> None:
        if cls.LLM_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file."
            )
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise EnvironmentError("OPENAI_API_KEY is not set. Add it to your .env file.")
        if cls.LLM_PROVIDER == "openrouter" and not cls.OPENROUTER_API_KEY:  # ← NEW
            raise EnvironmentError("OPENROUTER_API_KEY is not set. Add it to your .env file.")
        if not cls.TAVILY_API_KEY:
            raise EnvironmentError("TAVILY_API_KEY is not set. Add it to your .env file.")


def get_llm(temperature: float = 0.3) -> BaseChatModel:
    Config.validate()

    if Config.LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=Config.LLM_MODEL,
            temperature=temperature,
            anthropic_api_key=Config.ANTHROPIC_API_KEY,
        )

    if Config.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=Config.LLM_MODEL,
            temperature=temperature,
            openai_api_key=Config.OPENAI_API_KEY,
        )

    if Config.LLM_PROVIDER == "openrouter":       # ← NEW BLOCK
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=Config.LLM_MODEL,
            temperature=temperature,
            openai_api_key=Config.OPENROUTER_API_KEY,
            base_url=Config.OPENROUTER_BASE_URL,
            default_headers={                     # ← OpenRouter strongly recommends these
                "HTTP-Referer": "https://your-app-name.com",
                "X-Title": "Your App Name",
            },
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER: '{Config.LLM_PROVIDER}'. "
        "Use 'anthropic', 'openai', or 'openrouter'."
    )