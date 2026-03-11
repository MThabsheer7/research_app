from agent.graph.state import ResearchState
from agent.llm_client import llm
from pydantic import BaseModel, Field
from typing import Literal, List
import time

# Node specific output schema
class PlannerOutput(BaseModel):
    needs_clarification: bool = Field(description="True if the user query is too vague to formulate a research plan")
    clarifying_questions: List[str] = Field(description="List of questions to ask the user if needs_clarification is True", default_factory=list)
    query_complexity: Literal["simple", "complex"] = Field(description="Whether the query requires simple answering or complex research")
    subquestions: List[str] = Field(description="The Research Plan: a list of specific search queries to execute, if complex", default_factory=list)
    reasoning: str = Field(description="Explanation of the generated plan or need for clarification")

SYSTEM_PROMPT = """
You are a Lead Research Agent. Your job is to analyze the user's research query and formulate a Research Plan.

If the user's query is highly ambiguous or lacks critical context to perform meaningful research, you should ask CLARIFYING QUESTIONS.
Do not ask clarifying questions if you can reasonably infer the user's intent.

If the query is straightforward and requires no research (e.g. definitions, general knowledge), mark it as "simple".

If the query requires gathering information, mark it as "complex" and generate a RESEARCH PLAN (a list of 'subquestions').
These subquestions will be executed by parallel search agents.
- Generate 3 to 6 targeted subquestions that break the main query down into specific search tasks.
- Make them standalone and highly specific.

If the user provides FEEDBACK on a previous plan, you MUST incorporate their feedback to refine the subquestions.
"""

def planner_node(state: ResearchState) -> dict:
    user_input = state["user_input"]
    user_feedback = state.get("user_feedback", "")
    
    # Construct the payload
    content = f"User Query: {user_input}\n"
    if user_feedback:
        content += f"\nUser Feedback/Edits on Previous Plan: {user_feedback}\n"
        content += "Please update the Research Plan based on this feedback."

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = llm.generate_structured(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content}
                ],
                response_format=PlannerOutput,
                max_tokens=1500
            )
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

    return {
        "query_complexity": result.query_complexity,
        "reasoning": result.reasoning,
        "clarifying_questions": result.clarifying_questions if result.needs_clarification else [],
        "subquestions": result.subquestions if result.query_complexity == "complex" and not result.needs_clarification else []
    }

def route_planner(state: ResearchState) -> str:
    # If the planner asks for clarification, route to Human-in-the-Loop Wait Node
    if state.get("clarifying_questions"):
        return "wait_for_user"
    
    if state["query_complexity"] == "complex":
        # We successfully generated subquestions, route to Wait Node for Plan Approval
        return "wait_for_user"
        
    # If it's a simple query, just synthesize
    return "synthesizer"