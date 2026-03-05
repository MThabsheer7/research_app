"""
Agent client — async wrapper around the LangGraph research graph.
In a microservice setup this would make an HTTP call to the agent service;
in the current monorepo it imports the compiled graph directly.
"""
import uuid
import os
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agent.graph.graph import research_graph

# Monkey-patch aiosqlite.Connection to support is_alive()
# langgraph-checkpoint-sqlite 2.0.11 expects this, but aiosqlite 0.20+ removed it.
if not hasattr(aiosqlite.Connection, "is_alive"):
    aiosqlite.Connection.is_alive = lambda self: self._running

_DB_PATH = os.environ.get("CHECKPOINT_DB", "data/checkpoints.db")
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)



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
    async with AsyncSqliteSaver.from_conn_string(_DB_PATH) as saver:
        app = research_graph.compile(checkpointer=saver)
        state = await app.ainvoke(
            _build_initial_state(query),
            config=config,
        )
    return thread_id, state


async def get_research_state(thread_id: str) -> dict | None:
    """
    Retrieve the last checkpoint for a given thread from SQLite.
    Returns None if the thread_id doesn't exist.
    """
    config = {"configurable": {"thread_id": thread_id}}
    async with AsyncSqliteSaver.from_conn_string(_DB_PATH) as saver:
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
    async with AsyncSqliteSaver.from_conn_string(_DB_PATH) as saver:
        app = research_graph.compile(checkpointer=saver)
        async for step in app.astream(
            _build_initial_state(query),
            config=config,
            stream_mode="updates"
        ):
            yield step
