from agent.graph.state import ResearchState
from langgraph.types import interrupt

def wait_for_user_node(state: ResearchState) -> dict:
    """
    This node pauses the graph execution to wait for user input.
    When the graph is resumed via `research_app.stream(Command(resume=...))`,
    the value passed to resume is returned by `interrupt()`.
    """
    
    # Pause execution and send this payload to the client so they know what to ask
    user_response = interrupt({
        "clarifying_questions": state.get("clarifying_questions", []),
        "subquestions": state.get("subquestions", [])
    })
    
    # When resumed, user_response will contain the payload from the client
    return {
        "user_feedback": user_response.get("user_feedback", ""),
        "plan_approved": user_response.get("plan_approved", False),
        "subquestions": user_response.get("subquestions", state.get("subquestions", []))
    }

def route_after_interaction(state: ResearchState) -> str:
    # If the user approved the plan, fan-out to the searchers
    if state.get("plan_approved"):
        return "dispatch_searchers"
    
    # Otherwise, the user submitted feedback or answered clarifying questions.
    # Send it back to the planner to rewrite the plan.
    return "planner"
