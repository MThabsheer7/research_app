import pytest
import uuid
import os
import sqlite3
from unittest.mock import patch, MagicMock
from agent.graph.state import ReportModel

# Try to clear SQLite path if testing locally
from api.services.agent_client import run_research, get_research_state, _build_initial_state

@pytest.mark.asyncio
async def test_run_research_generates_thread_id():
    """
    Test that run_research generates a thread_id and invokes the research app.
    We mock ainvoke to avoid actually running the agent pipeline.
    """
    mock_state_output = {
        "user_input": "Is this a test?",
        "query_complexity": "simple",
        "subquestions": [],
        "search_results": [],
        "failed_tasks": [],
        "final_report": ReportModel(
            summary="Yes, it is a test.",
            sentences=[]
        ),
        "iteration_count": 1,
        "reasoning": ""
    }
    
    with patch("api.services.agent_client.research_app.ainvoke") as mock_ainvoke:
        mock_ainvoke.return_value = mock_state_output
        
        thread_id, state = await run_research("Is this a test?")
        
        assert isinstance(thread_id, str)
        assert len(thread_id) > 10 # Check it's a UUID-like string
        assert state == mock_state_output
        
        # Verify ainvoke was called with right arguments
        called_state, called_kwargs = mock_ainvoke.call_args
        assert called_state[0] == _build_initial_state("Is this a test?")
        assert called_kwargs["config"]["configurable"]["thread_id"] == thread_id


def test_get_research_state_returns_none_if_not_found():
    """
    Test get_research_state behaves correctly when thread_id does not exist.
    """
    with patch("api.services.agent_client.research_app.get_state") as mock_get_state:
        # Mock StateSnapshot returning empty values
        mock_snapshot = MagicMock()
        mock_snapshot.values = {}
        mock_get_state.return_value = mock_snapshot
        
        result = get_research_state("non-existent-thread")
        assert result is None
        
        # Or mock returning None
        mock_get_state.return_value = None
        result2 = get_research_state("non-existent-thread-2")
        assert result2 is None

def test_get_research_state_returns_values_if_found():
    """
    Test get_research_state returns the state dictionary if checkpoint exists.
    """
    with patch("api.services.agent_client.research_app.get_state") as mock_get_state:
        mock_values = {"user_input": "Test thread", "query_complexity": "simple"}
        
        mock_snapshot = MagicMock()
        mock_snapshot.values = mock_values
        mock_get_state.return_value = mock_snapshot
        
        result = get_research_state("existent-thread")
        
        assert result == mock_values
        mock_get_state.assert_called_once()
        config_arg = mock_get_state.call_args[0][0]
        assert config_arg["configurable"]["thread_id"] == "existent-thread"
