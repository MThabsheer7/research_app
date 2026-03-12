import sys
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Psycopg (used by LangGraph Postgres Checkpointer) requires SelectorEventLoop on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

from api.routes.research import router as research_router
from api.routes.ws import router as ws_router

app = FastAPI(
    title="Research Agent API",
    description="Multi-agent research system powered by LangGraph and Qwen3.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers after middleware
app.include_router(research_router, prefix="/api/v1", tags=["research"])
app.include_router(ws_router, tags=["websocket"])

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Research Agent API is running. See /docs for usage."}
