"""
Agent client — async wrapper around the LangGraph research graph.
In a microservice setup this would make an HTTP call to the agent service;
in the current monorepo it imports the compiled graph directly.
"""
from agent.graph.graph import research_app


def _build_initial_state(query: str) -> dict:
    return {
        "user_input": query,
        "subquestions": [],
        "search_results": [],
        "failed_tasks": [],
        "final_report": None,
        "iteration_count": 0,
        "query_complexity": "simple",
        "reasoning": "",
    }


async def run_research(query: str) -> dict:
    """
    Invoke the research graph asynchronously and return the final state.
    Raises exceptions from the graph unhandled — callers should catch them.
    """
    config = {"recursion_limit": 25}
    state = await research_app.ainvoke(
        _build_initial_state(query),
        config=config,
    )
    return state
