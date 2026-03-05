"""
Agent client — async wrapper around the LangGraph research graph.
In a microservice setup this would make an HTTP call to the agent service;
in the current monorepo it imports the compiled graph directly.
"""
import uuid
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


async def run_research(query: str) -> tuple[str, dict]:
    """
    Invoke the research graph asynchronously.
    Returns (thread_id, final_state) — thread_id lets clients retrieve results later.
    """
    thread_id = str(uuid.uuid4())
    config = {
        "recursion_limit": 25,
        "configurable": {"thread_id": thread_id},  # ← ties this run to a SQLite checkpoint
    }
    state = await research_app.ainvoke(
        _build_initial_state(query),
        config=config,
    )
    return thread_id, state


def get_research_state(thread_id: str) -> dict | None:
    """
    Retrieve the last checkpoint for a given thread from SQLite.
    Returns None if the thread_id doesn't exist.
    """
    config = {"configurable": {"thread_id": thread_id}}
    checkpoint = research_app.get_state(config)
    # get_state returns a StateSnapshot; .values is the state dict (empty if not found)
    if not checkpoint or not checkpoint.values:
        return None
    return checkpoint.values
