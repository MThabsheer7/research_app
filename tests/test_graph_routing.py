"""
Tests for graph routing logic — route_planner and route_synthesizer.
These tests verify the conditional edge functions in isolation (no LLM calls).
"""
import pytest
from agent.graph.nodes.planner import route_planner
from agent.graph.nodes.synthesizer import route_synthesizer, MAX_ITERATIONS


def make_state(
    query_complexity="simple",
    subquestions=None,
    failed_tasks=None,
    iteration_count=0,
):
    """Helper to build a minimal ResearchState for routing tests."""
    return {
        "user_input": "test query",
        "subquestions": subquestions or [],
        "search_results": [],
        "failed_tasks": failed_tasks or [],
        "final_report": None,
        "iteration_count": iteration_count,
        "planner_iteration_count": 0,
        "query_complexity": query_complexity,
        "clarifying_questions": [],
        "user_feedback": "",
        "plan_approved": False,
    }


class TestRoutePlanner:
    def test_simple_query_routes_to_synthesizer(self):
        state = make_state(query_complexity="simple")
        assert route_planner(state) == "synthesizer"

    def test_complex_query_routes_to_wait_for_user(self):
        state = make_state(query_complexity="complex")
        assert route_planner(state) == "wait_for_user"
        
    def test_clarifying_questions_routes_to_wait_for_user(self):
        state = make_state()
        state["clarifying_questions"] = ["What do you mean?"]
        assert route_planner(state) == "wait_for_user"
        
    def test_max_planner_iterations_routes_to_synthesizer_if_simple(self):
        state = make_state(query_complexity="simple")
        state["planner_iteration_count"] = 3
        assert route_planner(state) == "synthesizer"
        
    def test_max_planner_iterations_routes_to_wait_for_user_if_complex(self):
        state = make_state(query_complexity="complex")
        state["planner_iteration_count"] = 3
        route = route_planner(state)
        assert route == "wait_for_user"
        assert state.get("plan_approved") is True


class TestRouteSynthesizer:
    def test_simple_query_always_done(self):
        """No subquestions = simple path, should always terminate."""
        state = make_state(subquestions=[], iteration_count=0)
        assert route_synthesizer(state) == "done"

    def test_max_iterations_reached_returns_done(self):
        state = make_state(
            subquestions=["q1", "q2", "q3"],
            iteration_count=MAX_ITERATIONS,
        )
        assert route_synthesizer(state) == "done"

    def test_enough_successes_returns_done(self):
        """3+ successful searches on first iteration should terminate (no retry needed)."""
        state = make_state(
            subquestions=["q1", "q2", "q3"],
            failed_tasks=[],  # 3 successes
            iteration_count=0,
        )
        assert route_synthesizer(state) == "done"

    def test_too_few_successes_returns_retry(self):
        """Fewer than 3 successes on a complex query should trigger retry."""
        state = make_state(
            subquestions=["q1", "q2", "q3"],
            failed_tasks=[{"query": "q1", "error": "timeout"},
                          {"query": "q2", "error": "timeout"}],  # only 1 success
            iteration_count=0,
        )
        assert route_synthesizer(state) == "retry"

    def test_retry_does_not_fire_after_max_iterations(self):
        """Even with few successes, must stop at max iterations."""
        state = make_state(
            subquestions=["q1", "q2", "q3"],
            failed_tasks=[{"query": "q1", "error": "timeout"},
                          {"query": "q2", "error": "timeout"}],
            iteration_count=MAX_ITERATIONS,
        )
        assert route_synthesizer(state) == "done"
