"""
Smoke test against the live vLLM endpoint.
Run with: python scripts/smoke_test_llm.py
"""
import os
import sys
sys.path.insert(0, r'D:\thabsheer\projects\research_app')
os.environ["LLM_BASE_URL"] = "https://ae3f-34-142-241-110.ngrok-free.app/v1"
os.environ["LLM_API_KEY"] = "not-needed"
os.environ["LLM_MODEL"] = "Qwen/Qwen3-4B"

from openai import OpenAI
from pydantic import BaseModel
from typing import Literal

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)
MODEL = os.environ["LLM_MODEL"]

# ── Test 1: Basic chat completion ───────────────────────────────────────────
print("Test 1: Basic chat completion")
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Say hello in one sentence."}],
    max_tokens=50,
)
print("  ->", resp.choices[0].message.content)
print("  PASSED\n")

# ── Test 2: Structured output ───────────────────────────────────────────────
class PlannerOutput(BaseModel):
    query_complexity: Literal["simple", "complex"]
    reasoning: str

print("Test 2: Structured output (beta.chat.completions.parse)")
resp2 = client.beta.chat.completions.parse(
    model=MODEL,
    messages=[
        {"role": "system",  "content": "Classify the query as simple or complex. Output JSON only."},
        {"role": "user",    "content": "What is the capital of France?"},
    ],
    response_format=PlannerOutput,
    max_tokens=100,
)
result = resp2.choices[0].message.parsed
print(f"  query_complexity = {result.query_complexity}")
print(f"  reasoning        = {result.reasoning}")
print("  PASSED\n")

print("All smoke tests passed!")
