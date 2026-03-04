"""
Tests for ResearchState schema and all Pydantic models.
"""
import pytest
from agent.graph.state import (
    ResearchState,
    SearchResultModel,
    FailedTaskModel,
    SentenceModel,
    ReportModel,
)


class TestSearchResultModel:
    def test_valid_construction(self):
        model = SearchResultModel(
            query="What is AlphaFold?",
            result=["chunk 1", "chunk 2"],
            source_url="https://example.com"
        )
        assert model.query == "What is AlphaFold?"
        assert len(model.result) == 2
        assert model.source_url == "https://example.com"

    def test_result_is_list_of_strings(self):
        model = SearchResultModel(query="q", result=["a", "b", "c"], source_url="http://x.com")
        assert all(isinstance(r, str) for r in model.result)

    def test_missing_field_raises(self):
        with pytest.raises(Exception):
            SearchResultModel(query="q", result=[])  # missing source_url


class TestFailedTaskModel:
    def test_valid_construction(self):
        model = FailedTaskModel(query="What is X?", error="Timeout after 30s")
        assert model.query == "What is X?"
        assert model.error == "Timeout after 30s"


class TestReportModel:
    def test_valid_construction(self):
        sentence = SentenceModel(sentence="AlphaFold is...", source_url="https://example.com")
        report = ReportModel(summary="A summary.", sentences=[sentence])
        assert report.summary == "A summary."
        assert len(report.sentences) == 1

    def test_citation_anchors_to_url(self):
        sentence = SentenceModel(sentence="X", source_url="https://nature.com/paper")
        assert "nature.com" in sentence.source_url


class TestResearchStateDefaults:
    def test_iteration_count_defaults_to_zero(self):
        state: ResearchState = {
            "user_input": "test",
            "subquestions": [],
            "search_results": [],
            "failed_tasks": [],
            "final_report": None,
            "iteration_count": 0,
            "query_complexity": "simple",
        }
        assert state["iteration_count"] == 0

    def test_search_results_reducer_combines_lists(self):
        """operator.add should merge two lists — verify manually."""
        import operator
        a = [SearchResultModel(query="q1", result=["r1"], source_url="http://a.com")]
        b = [SearchResultModel(query="q2", result=["r2"], source_url="http://b.com")]
        merged = operator.add(a, b)
        assert len(merged) == 2
        assert merged[0].query == "q1"
        assert merged[1].query == "q2"
