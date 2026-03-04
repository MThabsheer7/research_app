"""
Shared LLM client for all agent nodes.
All nodes should import `llm_client` from here rather than instantiating their own.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

llm_client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)

# Model name registered in vLLM — update if serving a different variant
LLM_MODEL = os.environ.get("LLM_MODEL", "Qwen/Qwen3-4B")
