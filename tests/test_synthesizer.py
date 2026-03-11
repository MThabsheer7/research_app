import os
import pytest
from unittest.mock import patch, MagicMock

# Set env vars BEFORE importing the module
os.environ.setdefault("LLM_BASE_URL", "http://fake-url/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")

from agent.graph.nodes.synthesizer import (
    synthesizer_node,
    _build_citation_map_and_context,
    CitedSentence,
    SynthesizerOutput,
    MAX_ITERATIONS,
)
from agent.graph.state import SearchResultModel, ReportModel, SentenceModel

PATCH_TARGET = "agent.graph.nodes.synthesizer.llm.generate_structured"


# ── Fixtures & helpers ────────────────────────────────────────────────────────

def make_search_result(query: str, chunks: list[str], urls: list[str]) -> SearchResultModel:
    return SearchResultModel(query=query, result=chunks, source_urls=urls)


def make_mock_response(summary: str, cited_sentences: list[tuple[str, int]]):
    """Build a fake structured output response matching SynthesizerOutput."""
    return SynthesizerOutput(
        summary=summary,
        sentences=[CitedSentence(sentence=s, ref=r) for s, r in cited_sentences],
    )


SEARCH_RESULT_1 = make_search_result(
    query="What is AlphaFold?",
    chunks=["AlphaFold predicts protein structures.", "It uses deep learning techniques."],
    urls=["https://deepmind.com/1", "https://deepmind.com/2"],
)
SEARCH_RESULT_2 = make_search_result(
    query="What are AlphaFold's limitations?",
    chunks=["AlphaFold struggles with protein complexes."],
    urls=["https://deepmind.com/3"],
)

BASE_STATE = {
    "user_input": "Explain AlphaFold and its limitations.",
    "subquestions": ["What is AlphaFold?", "What are AlphaFold's limitations?"],
    "search_results": [SEARCH_RESULT_1, SEARCH_RESULT_2],
    "failed_tasks": [],
    "final_report": None,
    "iteration_count": 0,
    "query_complexity": "complex",
    "reasoning": "Requires multi-source research.",
}


# ── Tests: _build_citation_map_and_context ────────────────────────────────────

class TestBuildCitationMap:
    def test_citation_map_sequential_keys(self):
        """Refs must be 1-indexed and sequential across all search results."""
        citation_map, _ = _build_citation_map_and_context([SEARCH_RESULT_1, SEARCH_RESULT_2])
        assert set(citation_map.keys()) == {1, 2, 3}

    def test_citation_map_urls_match_chunks(self):
        """Each ref must point to the correct source URL for its chunk."""
        citation_map, _ = _build_citation_map_and_context([SEARCH_RESULT_1, SEARCH_RESULT_2])
        assert citation_map[1] == "https://deepmind.com/1"
        assert citation_map[2] == "https://deepmind.com/2"
        assert citation_map[3] == "https://deepmind.com/3"

    def test_context_block_contains_subquestions(self):
        """Context block must include each subquestion as a header."""
        _, context = _build_citation_map_and_context([SEARCH_RESULT_1, SEARCH_RESULT_2])
        assert "What is AlphaFold?" in context
        assert "What are AlphaFold's limitations?" in context

    def test_context_block_contains_numbered_chunks(self):
        """Each chunk must appear in the context with its [N] reference."""
        _, context = _build_citation_map_and_context([SEARCH_RESULT_1])
        assert "[1] AlphaFold predicts protein structures." in context
        assert "[2] It uses deep learning techniques." in context


# ── Tests: synthesizer_node ───────────────────────────────────────────────────

class TestSynthesizerNode:
    def test_returns_final_report_key(self):
        """Returned dict must contain 'final_report'."""
        mock_resp = make_mock_response("Overview.", [("AlphaFold is a system. [1]", 1)])
        with patch(PATCH_TARGET, return_value=mock_resp):
            result = synthesizer_node(BASE_STATE)
            assert "final_report" in result

    def test_final_report_is_report_model(self):
        """final_report must be a ReportModel instance."""
        mock_resp = make_mock_response("Overview.", [("AlphaFold is a system.", 1)])
        with patch(PATCH_TARGET, return_value=mock_resp):
            result = synthesizer_node(BASE_STATE)
            assert isinstance(result["final_report"], ReportModel)

    def test_iteration_count_incremented(self):
        """synthesizer_node must always increment iteration_count."""
        mock_resp = make_mock_response("Overview.", [("AlphaFold is a system.", 1)])
        with patch(PATCH_TARGET, return_value=mock_resp):
            result = synthesizer_node(BASE_STATE)
            assert result["iteration_count"] == BASE_STATE["iteration_count"] + 1

    def test_ref_correctly_mapped_to_url(self):
        """Cited ref index must resolve to the correct source URL."""
        mock_resp = make_mock_response("Overview.", [
            ("AlphaFold predicts protein structures.", 1),   # ref 1 -> deepmind.com/1
            ("AlphaFold struggles with complexes.", 3),      # ref 3 -> deepmind.com/3
        ])
        with patch(PATCH_TARGET, return_value=mock_resp):
            result = synthesizer_node(BASE_STATE)
            sentences = result["final_report"].sentences
            assert sentences[0].source_url == "https://deepmind.com/1"
            assert sentences[1].source_url == "https://deepmind.com/3"

    def test_hallucinated_ref_falls_back_to_empty_string(self):
        """A ref index not in citation_map must fall back to '' not raise."""
        mock_resp = make_mock_response("Overview.", [
            ("Made-up fact.", 999),   # ref 999 doesn't exist
        ])
        with patch(PATCH_TARGET, return_value=mock_resp):
            result = synthesizer_node(BASE_STATE)
            sentences = result["final_report"].sentences
            assert sentences[0].source_url == ""  # graceful fallback

    def test_sentences_are_sentence_models(self):
        """Each sentence in the report must be a SentenceModel."""
        mock_resp = make_mock_response("Overview.", [
            ("AlphaFold predicts protein structures.", 1),
        ])
        with patch(PATCH_TARGET, return_value=mock_resp):
            result = synthesizer_node(BASE_STATE)
            for s in result["final_report"].sentences:
                assert isinstance(s, SentenceModel)

    def test_simple_query_no_search_results(self):
        """With empty search_results (simple query), must return answer from LLM."""
        simple_state = {**BASE_STATE, "search_results": [], "subquestions": [], "user_input": "Test query"}
        
        with patch("agent.graph.nodes.synthesizer.llm.generate_text", return_value="Direct answer.") as mock_generate_text:
            with patch(PATCH_TARGET) as mock_parse:
                result = synthesizer_node(simple_state)
                mock_parse.assert_not_called()
                mock_generate_text.assert_called_once()
                assert "final_report" in result
                assert result["final_report"].summary == "Direct answer."
                assert result["iteration_count"] == simple_state["iteration_count"] + 1

    def test_retries_on_transient_failure(self):
        """Fails twice, succeeds on third attempt."""
        success = make_mock_response("Overview.", [("Sentence.", 1)])
        with patch(PATCH_TARGET) as mock_parse:
            with patch("agent.graph.nodes.synthesizer.time.sleep") as mock_sleep:
                mock_parse.side_effect = [
                    ConnectionError("timeout"),
                    ConnectionError("timeout"),
                    success,
                ]
                result = synthesizer_node(BASE_STATE)
                assert "final_report" in result
                assert mock_parse.call_count == 3
                assert mock_sleep.call_count == 2

    def test_raises_after_max_retries_exhausted(self):
        """All attempts fail — exception must propagate out."""
        with patch(PATCH_TARGET, side_effect=ConnectionError("service down")):
            with patch("agent.graph.nodes.synthesizer.time.sleep"):
                with pytest.raises(ConnectionError):
                    synthesizer_node(BASE_STATE)
