from agent.graph.state import ResearchState

MAX_ITERATIONS = 5


def synthesizer_node(state: ResearchState) -> dict:
    return {"iteration_count": state["iteration_count"] + 1}

def route_synthesizer(state: ResearchState) -> str:
    # Always stop if we've hit the iteration cap
    if state["iteration_count"] >= MAX_ITERATIONS:
        return "done"
    # Simple query path — no subquestions, nothing to retry
    if not state["subquestions"]:
        return "done"
    # Complex query — only retry if we had enough successful searches
    successful = len(state["subquestions"]) - len(state["failed_tasks"])
    if successful < 3:
        return "retry"
    return "done"