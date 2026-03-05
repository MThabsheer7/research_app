from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from api.routes.research import router as research_router

app = FastAPI(
    title="Research Agent API",
    description="Multi-agent research system powered by LangGraph and Qwen3.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router, prefix="/api/v1", tags=["research"])


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Research Agent API is running. See /docs for usage."}
