import pytest
import uuid
import os
from unittest.mock import patch, MagicMock, AsyncMock
from agent.graph.state import ReportModel

# Try to clear checkpoint path if testing locally
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
        "planner_iteration_count": 1,
        "reasoning": "",
        "clarifying_questions": [],
        "user_feedback": "",
        "plan_approved": False,
    }
    
    with patch("api.services.agent_client.AsyncPostgresSaver") as mock_saver_cls:
        # Mock the async context manager
        mock_saver_inst = AsyncMock()
        mock_saver_cls.from_conn_string.return_value = mock_saver_inst
        mock_saver_inst.__aenter__.return_value = mock_saver_inst
        
        with patch("api.services.agent_client.research_graph.compile") as mock_compile:
            mock_compiled_graph = MagicMock()
            mock_compiled_graph.ainvoke = AsyncMock(return_value=mock_state_output)
            mock_compile.return_value = mock_compiled_graph
            
            thread_id, state = await run_research("Is this a test?")
            
            assert isinstance(thread_id, str)
            assert len(thread_id) > 10 # Check it's a UUID-like string
            assert state == mock_state_output
            
            # Verify ainvoke was called with right arguments
            called_state, called_kwargs = mock_compiled_graph.ainvoke.call_args
            assert called_state[0] == _build_initial_state("Is this a test?")
            assert called_kwargs["config"]["configurable"]["thread_id"] == thread_id


@pytest.mark.asyncio
async def test_get_research_state_returns_none_if_not_found():
    """
    Test get_research_state behaves correctly when thread_id does not exist.
    """
    with patch("api.services.agent_client.AsyncPostgresSaver") as mock_saver_cls:
        mock_saver_inst = AsyncMock()
        mock_saver_cls.from_conn_string.return_value = mock_saver_inst
        mock_saver_inst.__aenter__.return_value = mock_saver_inst

        with patch("api.services.agent_client.research_graph.compile") as mock_compile:
            mock_compiled_graph = MagicMock()
            mock_compile.return_value = mock_compiled_graph
            
            # Mock StateSnapshot returning empty values
            mock_snapshot = MagicMock()
            mock_snapshot.values = {}
            mock_compiled_graph.aget_state = AsyncMock(return_value=mock_snapshot)
            
            result = await get_research_state("non-existent-thread")
            assert result is None
            
            # Or mock returning None
            mock_compiled_graph.aget_state = AsyncMock(return_value=None)
            result2 = await get_research_state("non-existent-thread-2")
            assert result2 is None

@pytest.mark.asyncio
async def test_get_research_state_returns_values_if_found():
    """
    Test get_research_state returns the state dictionary if checkpoint exists.
    """
    with patch("api.services.agent_client.AsyncPostgresSaver") as mock_saver_cls:
        mock_saver_inst = AsyncMock()
        mock_saver_cls.from_conn_string.return_value = mock_saver_inst
        mock_saver_inst.__aenter__.return_value = mock_saver_inst

        with patch("api.services.agent_client.research_graph.compile") as mock_compile:
            mock_compiled_graph = MagicMock()
            mock_compile.return_value = mock_compiled_graph
            
            mock_values = {"user_input": "Test thread", "query_complexity": "simple"}
            
            mock_snapshot = MagicMock()
            mock_snapshot.values = mock_values
            mock_compiled_graph.aget_state = AsyncMock(return_value=mock_snapshot)
            
            result = await get_research_state("existent-thread")
            
            assert result == mock_values
            mock_compiled_graph.aget_state.assert_called_once()
            config_arg = mock_compiled_graph.aget_state.call_args[0][0]
            assert config_arg["configurable"]["thread_id"] == "existent-thread"
