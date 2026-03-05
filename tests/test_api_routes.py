import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app
from agent.graph.state import ReportModel, SentenceModel

client = TestClient(app)

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("api.routes.research.run_research")
def test_post_research_success(mock_run_research):
    # Mock the async function
    import asyncio
    
    mock_state = {
        "user_input": "Test query",
        "query_complexity": "simple",
        "subquestions": [],
        "search_results": [],
        "failed_tasks": [],
        "final_report": ReportModel(
            summary="A short summary.",
            sentences=[SentenceModel(sentence="It is a test.", source_url="http://test.com")]
        ),
        "iteration_count": 1,
        "reasoning": ""
    }

    async def mock_run_fn(query):
        return ("thread-123", mock_state)
        
    mock_run_research.side_effect = mock_run_fn

    response = client.post(
        "/api/v1/research",
        json={"query": "Test query"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "thread-123"
    assert data["summary"] == "A short summary."
    assert len(data["sentences"]) == 1
    assert data["sentences"][0]["sentence"] == "It is a test."
    assert data["sentences"][0]["source_url"] == "http://test.com"

def test_post_research_empty_query():
    response = client.post(
        "/api/v1/research",
        json={"query": "   "}
    )
    assert response.status_code == 422
    assert "Query must not be empty" in response.json()["detail"]

@patch("api.routes.research.run_research")
def test_post_research_exception(mock_run_research):
    async def mock_run_fn(query):
        raise ValueError("Something went wrong.")
        
    mock_run_research.side_effect = mock_run_fn

    response = client.post(
        "/api/v1/research",
        json={"query": "Test query"}
    )
    assert response.status_code == 500
    assert "Agent error: Something went wrong." in response.json()["detail"]

@patch("api.routes.research.get_research_state")
def test_get_research_success(mock_get_state):
    mock_state = {
        "user_input": "Test query",
        "query_complexity": "complex",
        "subquestions": ["q1", "q2"],
        "search_results": [],
        "failed_tasks": [],
        "final_report": ReportModel(
            summary="Historical report.",
            sentences=[]
        ),
        "iteration_count": 2,
        "reasoning": ""
    }
    mock_get_state.return_value = mock_state

    response = client.get("/api/v1/research/thread-123")
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "thread-123"
    assert data["query"] == "Test query"
    assert data["summary"] == "Historical report."
    assert data["query_complexity"] == "complex"

@patch("api.routes.research.get_research_state")
def test_get_research_not_found(mock_get_state):
    mock_get_state.return_value = None

    response = client.get("/api/v1/research/thread-404")
    assert response.status_code == 404
    assert "No research found" in response.json()["detail"]
