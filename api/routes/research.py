from fastapi import APIRouter, HTTPException
from api.models.research import ResearchRequest, ResearchResponse, CitedSentenceResponse
from api.services.agent_client import run_research

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    """
    Run the research agent on a user query.
    Returns a grounded report with cited sentences.
    """
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be empty.")

    try:
        state = await run_research(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    report = state.get("final_report")

    return ResearchResponse(
        query=request.query,
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
