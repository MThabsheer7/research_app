import os
import pytest
from unittest.mock import patch, MagicMock

# Set env vars BEFORE importing the module
os.environ.setdefault("LLM_BASE_URL", "http://fake-url/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")

from agent.graph.nodes.decomposer import decomposer_node, SubQuestionsModel

PATCH_TARGET = "agent.llm_client.llm_client.beta.chat.completions.parse"


def make_mock_response(subquestions: list[str]):
    """Build a fake response object mimicking client.beta.chat.completions.parse()."""
    parsed = SubQuestionsModel(subquestions=subquestions)
    choice = MagicMock()
    choice.message.parsed = parsed
    response = MagicMock()
    response.choices = [choice]
    return response


BASE_STATE = {
    "user_input": "Compare LangGraph and AutoGen for building multi-agent systems.",
    "reasoning": "This requires comparing multiple frameworks across different dimensions.",
}

SAMPLE_SUBQUESTIONS = [
    "What is LangGraph and how does it support multi-agent systems?",
    "What is AutoGen and how is it used for multi-agent workflows?",
    "What are the key architectural differences between LangGraph and AutoGen?",
    "What are the advantages and limitations of each framework?",
]


class TestDecomposerNode:
    def test_returns_subquestions_key(self):
        """Returned dict must have 'subquestions' key matching ResearchState field."""
        with patch(PATCH_TARGET) as mock_parse:
            mock_parse.return_value = make_mock_response(SAMPLE_SUBQUESTIONS)
            result = decomposer_node(BASE_STATE)
            assert "subquestions" in result

    def test_subquestions_is_list_of_strings(self):
        """Every subquestion must be a non-empty string."""
        with patch(PATCH_TARGET) as mock_parse:
            mock_parse.return_value = make_mock_response(SAMPLE_SUBQUESTIONS)
            result = decomposer_node(BASE_STATE)
            assert isinstance(result["subquestions"], list)
            assert all(isinstance(q, str) and q.strip() for q in result["subquestions"])

    def test_minimum_subquestions_count(self):
        """Decomposer should produce at least 3 subquestions for a complex query."""
        with patch(PATCH_TARGET) as mock_parse:
            mock_parse.return_value = make_mock_response(SAMPLE_SUBQUESTIONS)
            result = decomposer_node(BASE_STATE)
            assert len(result["subquestions"]) >= 3

    def test_does_not_write_unexpected_fields(self):
        """Node must only return 'subquestions' — no stray keys that corrupt state."""
        with patch(PATCH_TARGET) as mock_parse:
            mock_parse.return_value = make_mock_response(SAMPLE_SUBQUESTIONS)
            result = decomposer_node(BASE_STATE)
            assert set(result.keys()) == {"subquestions"}

    def test_uses_user_input_and_reasoning(self):
        """Verify the LLM call receives both user_input and reasoning in the message."""
        with patch(PATCH_TARGET) as mock_parse:
            mock_parse.return_value = make_mock_response(SAMPLE_SUBQUESTIONS)
            decomposer_node(BASE_STATE)
            call_kwargs = mock_parse.call_args
            # Find the user message content
            messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
            user_message = next(m for m in messages if m["role"] == "user")
            assert BASE_STATE["user_input"] in user_message["content"]
            assert BASE_STATE["reasoning"] in user_message["content"]

    def test_retries_on_transient_failure(self):
        """Fails twice, succeeds on third — result should still be correct."""
        success = make_mock_response(SAMPLE_SUBQUESTIONS)
        with patch(PATCH_TARGET) as mock_parse:
            with patch("agent.graph.nodes.decomposer.time.sleep") as mock_sleep:
                mock_parse.side_effect = [
                    ConnectionError("timeout"),
                    ConnectionError("timeout"),
                    success,
                ]
                result = decomposer_node(BASE_STATE)
                assert result["subquestions"] == SAMPLE_SUBQUESTIONS
                assert mock_parse.call_count == 3
                assert mock_sleep.call_count == 2
                mock_sleep.assert_any_call(1)   # 2 ** 0
                mock_sleep.assert_any_call(2)   # 2 ** 1

    def test_raises_after_max_retries_exhausted(self):
        """All 3 attempts fail — exception must propagate."""
        with patch(PATCH_TARGET) as mock_parse:
            with patch("agent.graph.nodes.decomposer.time.sleep"):
                mock_parse.side_effect = ConnectionError("service unavailable")
                with pytest.raises(ConnectionError):
                    decomposer_node(BASE_STATE)
                assert mock_parse.call_count == 3