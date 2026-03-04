"""
End-to-end integration test for the research agent graph.
Streams per-node state updates so you can trace every state change.

Usage:
    python scripts/e2e_test.py
"""
import os, sys, textwrap
sys.path.insert(0, r'D:\thabsheer\projects\research_app')

from dotenv import load_dotenv
load_dotenv()

from agent.graph.graph import research_app

QUERY = "Compare LangGraph, AutoGen, and CrewAI for building multi-agent systems."

INITIAL_STATE = {
    "user_input": QUERY,
    "subquestions": [],
    "search_results": [],
    "failed_tasks": [],
    "final_report": None,
    "iteration_count": 0,
    "query_complexity": "simple",
    "reasoning": "",
}

DIVIDER = "=" * 70

def truncate(text: str, n: int = 120) -> str:
    return (text[:n] + "...") if len(text) > n else text

print(DIVIDER)
print(f"Query: {QUERY}")
print(DIVIDER)

# ── Stream per-node state updates ─────────────────────────────────────────────
config = {"recursion_limit": 25}
final_state = None

for step in research_app.stream(INITIAL_STATE, config=config, stream_mode="updates"):
    for node_name, state_update in step.items():
        print(f"\n[{node_name.upper()}] state update:")

        if node_name == "planner":
            print(f"  query_complexity : {state_update.get('query_complexity')}")
            print(f"  reasoning        : {truncate(state_update.get('reasoning', ''))}")

        elif node_name == "decomposer":
            subqs = state_update.get("subquestions", [])
            print(f"  subquestions ({len(subqs)}):")
            for i, q in enumerate(subqs, 1):
                print(f"    {i}. {q}")

        elif node_name == "context_enhancer":
            sr   = state_update.get("search_results", [])
            ft   = state_update.get("failed_tasks", [])
            if sr:
                r = sr[0]
                print(f"  subquestion : {r.query}")
                print(f"  chunks      : {len(r.result)}")
                print(f"  top chunk   : {truncate(r.result[0])}")
                print(f"  source      : {r.source_urls[0]}")
            if ft:
                print(f"  FAILED: {ft[0].query} -> {ft[0].error}")

        elif node_name == "synthesizer":
            report = state_update.get("final_report")
            icount = state_update.get("iteration_count")
            print(f"  iteration_count : {icount}")
            if report:
                print(f"  summary         : {truncate(report.summary, 200)}")
                print(f"  sentences       : {len(report.sentences)}")
                for i, s in enumerate(report.sentences, 1):
                    print(f"    [{i}] {truncate(s.sentence, 100)}")
                    print(f"         -> {s.source_url}")

        else:
            # Generic fallback for any node
            for k, v in state_update.items():
                print(f"  {k}: {truncate(str(v))}")

    final_state = step

print(f"\n{DIVIDER}")
print("FINAL REPORT")
print(DIVIDER)
if final_state:
    for _, state_update in final_state.items():
        report = state_update.get("final_report")
        if report:
            print(f"\nSummary:\n  {textwrap.fill(report.summary, 70, subsequent_indent='  ')}")
            print(f"\nCited Sentences:")
            for i, s in enumerate(report.sentences, 1):
                wrapped = textwrap.fill(s.sentence, 66, subsequent_indent="     ")
                print(f"  [{i}] {wrapped}")
                print(f"       -> {s.source_url}")

print(f"\n{DIVIDER}")
print("End-to-end test complete.")
