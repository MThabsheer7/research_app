import os
import pytest
from unittest.mock import patch, MagicMock, call

# Set env vars BEFORE importing the module
os.environ.setdefault("LLM_BASE_URL", "http://fake-url/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")

from agent.graph.nodes.planner import planner_node, PlannerOutput

PATCH_TARGET = "agent.graph.nodes.planner.llm.generate_structured"


def make_mock_response(complexity: str, reasoning: str, needs_clarification=False, clarifying_questions=None, subquestions=None):
    """Build a fake parsed PlannerOutput"""
    return PlannerOutput(
        needs_clarification=needs_clarification,
        clarifying_questions=clarifying_questions or [],
        query_complexity=complexity,
        subquestions=subquestions or [],
        reasoning=reasoning
    )


class TestPlannerNode:
    BASE_STATE = {"user_input": "What is AlphaFold?"}

    def test_classifies_simple_query(self):
        with patch(PATCH_TARGET) as mock_parse:
            mock_parse.return_value = make_mock_response("simple", "well-known concept")
            result = planner_node(self.BASE_STATE)
            assert result["query_complexity"] == "simple"
            assert result["reasoning"] != ""
            assert result["subquestions"] == []
            assert result["clarifying_questions"] == []

    def test_classifies_complex_query(self):
        with patch(PATCH_TARGET) as mock_parse:
            mock_parse.return_value = make_mock_response("complex", "requires research", subquestions=["1", "2"])
            result = planner_node(self.BASE_STATE)
            assert result["query_complexity"] == "complex"
            assert result["subquestions"] == ["1", "2"]
            assert result["planner_iteration_count"] == 1
            
    def test_needs_clarification(self):
        with patch(PATCH_TARGET) as mock_parse:
            mock_parse.return_value = make_mock_response("complex", "ambiguous", needs_clarification=True, clarifying_questions=["q1?"])
            result = planner_node(self.BASE_STATE)
            assert result["clarifying_questions"] == ["q1?"]
            # Even if complex, subquestions should be empty if clarification is needed
            assert result["subquestions"] == []

    def test_retries_on_transient_failure(self):
        """Fails twice, succeeds on third attempt."""
        success_response = make_mock_response("simple", "ok")
        with patch(PATCH_TARGET) as mock_parse:
            with patch("agent.graph.nodes.planner.time.sleep") as mock_sleep:
                mock_parse.side_effect = [
                    ConnectionError("timeout"),
                    ConnectionError("timeout"),
                    success_response,
                ]
                result = planner_node(self.BASE_STATE)
                assert result["query_complexity"] == "simple"
                assert mock_parse.call_count == 3
                assert mock_sleep.call_count == 2          # slept after attempt 0 and 1
                mock_sleep.assert_any_call(1)              # 2 ** 0
                mock_sleep.assert_any_call(2)              # 2 ** 1

    def test_raises_after_max_retries_exhausted(self):
        """All attempts fail — exception must propagate."""
        with patch(PATCH_TARGET) as mock_parse:
            with patch("agent.graph.nodes.planner.time.sleep"):
                mock_parse.side_effect = ConnectionError("service unavailable")
                with pytest.raises(ConnectionError):
                    planner_node(self.BASE_STATE)
                assert mock_parse.call_count == 3          # tried 3 times
