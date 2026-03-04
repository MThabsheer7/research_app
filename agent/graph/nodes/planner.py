from agent.graph.state import ResearchState
from agent.llm_client import llm_client, LLM_MODEL
from pydantic import BaseModel
from typing import Literal
import time

# Node specific output schema
class PlannerOutput(BaseModel):
    query_complexity: Literal["simple", "complex"]
    reasoning: str


SYSTEM_PROMPT = """
You are a research assistant that helps users with their research queries.

You are given a research query and you must determine whether the query is SIMPLE or COMPLEX.

Definitions:

SIMPLE queries:
- Can be answered using general knowledge of an LLM.
- Do NOT require external information retrieval or web search.
- Usually involve explanations, definitions, comparisons, or well-known facts.

COMPLEX queries:
- Require gathering information from multiple sources.
- Require breaking the problem into multiple sub-questions.
- Often involve recent events, niche topics, research comparisons, statistics, or detailed analysis.

Your task:
Classify the query as "simple" or "complex".

Output format (JSON only):
{
    "query_complexity": "simple" | "complex",
    "reasoning": "Short explanation for why the query is simple or complex"
}

Below are examples.

Example 1
Query:
"What is the difference between supervised and unsupervised learning?"

Output:
{
    "query_complexity": "simple",
    "reasoning": "This is a conceptual explanation that can be answered using general machine learning knowledge without external search."
}

Example 2
Query:
"Explain how transformers work in large language models."

Output:
{
    "query_complexity": "simple",
    "reasoning": "The transformer architecture is well known and can be explained using existing knowledge without needing external research."
}

Example 3
Query:
"What are the latest advancements in quantum computing in 2025?"

Output:
{
    "query_complexity": "complex",
    "reasoning": "This requires up-to-date information and likely multiple sources describing recent developments in quantum computing."
}

Example 4
Query:
"Compare LangGraph, AutoGen, and CrewAI for building multi-agent systems."

Output:
{
    "query_complexity": "complex",
    "reasoning": "This requires gathering information about multiple frameworks and comparing their features and capabilities."
}

Example 5
Query:
"What are the health benefits of intermittent fasting?"

Output:
{
    "query_complexity": "simple",
    "reasoning": "General health information about intermittent fasting is widely known and does not require web search."
}

Example 6
Query:
"What are the best open-source tools for building LLM agents in 2025?"

Output:
{
    "query_complexity": "complex",
    "reasoning": "This requires collecting information about multiple tools and potentially recent developments in the LLM ecosystem."
}

Now classify the following query.
"""

def planner_node(state: ResearchState) -> dict:
    user_input = state["user_input"]

    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            response = llm_client.beta.chat.completions.parse(
                model=LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": user_input
                    }
                ],
                response_format=PlannerOutput
            )
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

    result: PlannerOutput = response.choices[0].message.parsed
    
    return {
        "query_complexity": result.query_complexity,
        "reasoning": result.reasoning
    }

def route_planner(state: ResearchState) -> str:
    return state["query_complexity"]