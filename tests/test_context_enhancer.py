import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# Set required env vars before importing modules
os.environ.setdefault("LLM_BASE_URL", "http://fake-url/v1")
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")

from agent.graph.nodes.context_enhancer import context_enhancer_node, TOP_K
from agent.graph.state import SearchResultModel, FailedTaskModel

TAVILY_PATCH  = "agent.graph.nodes.context_enhancer._tavily.search"
EMBEDDER_PATCH = "agent.graph.nodes.context_enhancer._embedder.encode"

SUBQUESTION = "What is AlphaFold and how does it work?"

# ── Mock helpers ────────────────────────────────────────────────────────────

def make_tavily_results(n: int = 5) -> dict:
    """Build a fake Tavily response with n results."""
    return {
        "results": [
            {"content": f"Chunk content {i} about AlphaFold.", "url": f"https://source{i}.com"}
            for i in range(n)
        ]
    }


def make_embeddings(n_chunks: int) -> np.ndarray:
    """
    Return fake normalized embeddings: [query_vec, chunk_vec_0, ..., chunk_vec_n].
    Each vector is a unit vector — cosine sim is deterministic and predictable.
    """
    dim = 8
    vecs = np.random.default_rng(42).random((1 + n_chunks, dim))
    # L2-normalize each row
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return (vecs / norms).astype(np.float32)


# ── Tests ────────────────────────────────────────────────────────────────────

class TestContextEnhancerNode:

    def test_returns_search_results_key(self):
        """Success path must return 'search_results' key."""
        with patch(TAVILY_PATCH, return_value=make_tavily_results(5)):
            with patch(EMBEDDER_PATCH, return_value=make_embeddings(5)):
                result = context_enhancer_node({"subquestion": SUBQUESTION})
                assert "search_results" in result

    def test_search_result_is_list_with_one_model(self):
        """Returns a list containing exactly one SearchResultModel per subquestion."""
        with patch(TAVILY_PATCH, return_value=make_tavily_results(5)):
            with patch(EMBEDDER_PATCH, return_value=make_embeddings(5)):
                result = context_enhancer_node({"subquestion": SUBQUESTION})
                assert len(result["search_results"]) == 1
                assert isinstance(result["search_results"][0], SearchResultModel)

    def test_result_has_at_most_top_k_chunks(self):
        """Result chunks must be capped at TOP_K even if Tavily returns more."""
        with patch(TAVILY_PATCH, return_value=make_tavily_results(7)):
            with patch(EMBEDDER_PATCH, return_value=make_embeddings(7)):
                result = context_enhancer_node({"subquestion": SUBQUESTION})
                model = result["search_results"][0]
                assert len(model.result) <= TOP_K

    def test_source_urls_parallel_to_chunks(self):
        """source_urls must have the same length as result chunks."""
        with patch(TAVILY_PATCH, return_value=make_tavily_results(5)):
            with patch(EMBEDDER_PATCH, return_value=make_embeddings(5)):
                result = context_enhancer_node({"subquestion": SUBQUESTION})
                model = result["search_results"][0]
                assert len(model.source_urls) == len(model.result)

    def test_query_field_matches_subquestion(self):
        """SearchResultModel.query must equal the dispatched subquestion."""
        with patch(TAVILY_PATCH, return_value=make_tavily_results(5)):
            with patch(EMBEDDER_PATCH, return_value=make_embeddings(5)):
                result = context_enhancer_node({"subquestion": SUBQUESTION})
                assert result["search_results"][0].query == SUBQUESTION

    def test_tavily_failure_returns_failed_task(self):
        """On Tavily error, node must return failed_tasks — not raise."""
        with patch(TAVILY_PATCH, side_effect=ConnectionError("Tavily unreachable")):
            result = context_enhancer_node({"subquestion": SUBQUESTION})
            assert "failed_tasks" in result
            assert "search_results" not in result
            assert isinstance(result["failed_tasks"][0], FailedTaskModel)
            assert result["failed_tasks"][0].query == SUBQUESTION

    def test_empty_tavily_results_returns_failed_task(self):
        """Empty results from Tavily should be treated as a failure."""
        with patch(TAVILY_PATCH, return_value={"results": []}):
            result = context_enhancer_node({"subquestion": SUBQUESTION})
            assert "failed_tasks" in result
            assert "no results" in result["failed_tasks"][0].error.lower()

    def test_failed_task_contains_error_message(self):
        """FailedTaskModel.error must be non-empty and describe the failure."""
        with patch(TAVILY_PATCH, side_effect=RuntimeError("API quota exceeded")):
            result = context_enhancer_node({"subquestion": SUBQUESTION})
            assert result["failed_tasks"][0].error != ""
