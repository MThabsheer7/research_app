"""
Entry point for the Research Agent API server.

Run this instead of `uvicorn api.main:app` on Windows, so that the correct
asyncio event loop policy is applied BEFORE uvicorn creates a loop.

Usage:
    python run.py
"""
import sys
import asyncio

# CRITICAL: Must be set before uvicorn creates the event loop.
# psycopg (used by LangGraph's Postgres checkpointer) requires SelectorEventLoop on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # Create and set the selector loop explicitly so uvicorn inherits it
    loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8001,
        loop="none",   # Tell uvicorn to use the already-created event loop above
    )

