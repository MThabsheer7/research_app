"""
Edge functions for the research graph.
Contains routing logic and Send()-based fan-out for parallel search.
"""
from langgraph.types import Send
from agent.graph.state import ResearchState


def dispatch_searchers(state: ResearchState) -> list[Send]:
    """
    Fan-out edge: dispatches one context_enhancer node per subquestion.
    Each invocation receives only the subquestion it needs to search.
    Results are merged back via the operator.add reducer on search_results.
    """
    return [
        Send("context_enhancer", {"subquestion": q})
        for q in state["subquestions"]
    ]
