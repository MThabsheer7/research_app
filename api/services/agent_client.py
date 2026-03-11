"""
Agent client — async wrapper around the LangGraph research graph.
In a microservice setup this would make an HTTP call to the agent service;
in the current monorepo it imports the compiled graph directly.
"""
import uuid
import os
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from agent.graph.graph import research_graph

_DB_URI = os.environ.get("POSTGRES_URI", "postgresql://postgres:postgres@localhost:5432/postgres")


def _build_initial_state(query: str) -> dict:
    return {
        "user_input": query,
        "subquestions": [],
        "search_results": [],
        "failed_tasks": [],
        "final_report": None,
        "iteration_count": 0,
        "planner_iteration_count": 0,
        "query_complexity": "simple",
        "reasoning": "",
        "clarifying_questions": [],
        "user_feedback": "",
        "plan_approved": False,
    }


async def run_research(query: str) -> tuple[str, dict]:
    """
    Invoke the research graph asynchronously.
    Returns (thread_id, final_state) — thread_id lets clients retrieve results later.
    """
    thread_id = str(uuid.uuid4())
    config = {
        "recursion_limit": 25,
        "configurable": {"thread_id": thread_id},  # ← ties this run to a Postgres checkpoint
    }
    async with AsyncPostgresSaver.from_conn_string(_DB_URI) as saver:
        await saver.setup()
        app = research_graph.compile(checkpointer=saver)
        state = await app.ainvoke(
            _build_initial_state(query),
            config=config,
        )
    return thread_id, state


async def get_research_state(thread_id: str) -> dict | None:
    """
    Retrieve the last checkpoint for a given thread from Postgres.
    Returns None if the thread_id doesn't exist.
    """
    config = {"configurable": {"thread_id": thread_id}}
    async with AsyncPostgresSaver.from_conn_string(_DB_URI) as saver:
        await saver.setup()
        app = research_graph.compile(checkpointer=saver)
        checkpoint = await app.aget_state(config)
        
    if not checkpoint or not checkpoint.values:
        return None
    return checkpoint.values


async def stream_research(query: str, thread_id: str):
    """
    Invoke the research graph asynchronously and yield stream updates.
    Useful for WebSocket endpoints to provide real-time progression.
    """
    config = {
        "recursion_limit": 25,
        "configurable": {"thread_id": thread_id},
    }
    async with AsyncPostgresSaver.from_conn_string(_DB_URI) as saver:
        await saver.setup()
        app = research_graph.compile(checkpointer=saver)
        async for step in app.astream(
            _build_initial_state(query),
            config=config,
            stream_mode="updates"
        ):
            yield step
