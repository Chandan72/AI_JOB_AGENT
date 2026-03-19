# test_config.py
from src.config import get_llm, Config

def test_connection():
    print(f"Provider : {Config.LLM_PROVIDER}")
    print(f"Model    : {Config.LLM_MODEL}")
    print(f"Testing connection...\n")

    llm = get_llm(temperature=0)
    response = llm.invoke("tell me why langsmith is useful for AI Architect, please be precise and to the point.")
    
    print(f"Response : {response.content}")
    print(f"✅ Connection successful!")

if __name__ == "__main__":
    test_connection()