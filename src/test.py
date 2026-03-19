import os
from config import Config
from langchain_anthropic import ChatAnthropic

Chat=ChatAnthropic(
    model=Config.LLM_MODEL,
    temperature=0.3,
    anthropic_api_key=Config.ANTHROPIC_API_KEY,
)

print(Chat.invoke("Hello, how are you?"))