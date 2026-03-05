from fastapi import APIRouter, HTTPException
from api.models.research import ResearchRequest, ResearchResponse, CitedSentenceResponse
from api.services.agent_client import run_research, get_research_state

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


def _state_to_response(query: str, thread_id: str, state: dict) -> ResearchResponse:
    """Convert a LangGraph state dict to the API response model."""
    report = state.get("final_report")
    return ResearchResponse(
        thread_id=thread_id,
        query=query,
        query_complexity=state.get("query_complexity", "simple"),
        subquestions=state.get("subquestions", []),
        summary=report.summary if report else "",
        sentences=[
            CitedSentenceResponse(sentence=s.sentence, source_url=s.source_url)
            for s in (report.sentences if report else [])
        ],
        failed_tasks=len(state.get("failed_tasks", [])),
        iteration_count=state.get("iteration_count", 0),
    )


@router.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """
    Run the research agent on a user query.
    Returns a grounded report with cited sentences and a thread_id for later retrieval.
    """
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty.")

    try:
        thread_id, state = await run_research(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    return _state_to_response(request.query, thread_id, state)


@router.get("/research/{thread_id}", response_model=ResearchResponse)
async def get_research(thread_id: str):
    """
    Retrieve the result of a past research run by its thread_id.
    Results are read directly from the SQLite checkpoint — no re-processing.
    """
    state = await get_research_state(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No research found for thread_id: {thread_id}")

    return _state_to_response(
        query=state.get("user_input", ""),
        thread_id=thread_id,
        state=state,
    )
