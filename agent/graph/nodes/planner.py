from agent.graph.state import ResearchState

def planner_node(state: ResearchState) -> dict:
    return {}

def route_planner(state: ResearchState) -> str:
    return state["query_complexity"]