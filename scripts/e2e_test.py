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

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from agent.graph.graph import research_graph

app = research_graph.compile(checkpointer=MemorySaver())

QUERY = "Compare LangGraph, AutoGen, and CrewAI for building multi-agent systems."

INITIAL_STATE = {
    "user_input": QUERY,
    "subquestions": [],
    "search_results": [],
    "failed_tasks": [],
    "final_report": None,
    "iteration_count": 0,
    "planner_iteration_count": 0,
    "query_complexity": "simple",
    "reasoning": "",
    "clarifying_questions": [],
    "user_feedback": "",
    "plan_approved": False,
}

DIVIDER = "=" * 70

def truncate(text: str, n: int = 120) -> str:
    return (text[:n] + "...") if len(text) > n else text

print(DIVIDER)
print(f"Query: {QUERY}")
print(DIVIDER)

# ── Stream per-node state updates ─────────────────────────────────────────────
config = {"configurable": {"thread_id": "e2e_test"}, "recursion_limit": 25}
final_state = None
iter_count = 0

for step in app.stream(INITIAL_STATE, config=config, stream_mode="updates"):
    for node_name, state_update in step.items():
        print(f"\n[{node_name.upper()}] state update:")

        if node_name == "__interrupt__":
            print("  [INTERRUPT] Execution paused by node.")
            print(f"  Interrupt data: {truncate(str(state_update))}")
        elif node_name == "planner":
            print(f"  query_complexity : {state_update.get('query_complexity')}")
            print(f"  reasoning        : {truncate(state_update.get('reasoning', ''))}")

        elif node_name == "wait_for_user":
            print(f"  [WAITING] The agent has paused to wait for user approval.")
            print(f"  Proposed subquestions: {state_update.get('subquestions', [])}")
            print(f"  [AUTO-RESPOND] Approving the research plan...")
        else:
            # Generic fallback for any node
            if isinstance(state_update, dict):
                for k, v in state_update.items():
                    print(f"  {k}: {truncate(str(v))}")
            else:
                print(f"  Data: {truncate(str(state_update))}")

    final_state = step

# If it stopped because of an interrupt, we must resume it by passing a Command
while iter_count < 2 and final_state and final_state.get("__interrupt__"):
    snapshot = app.get_state(config)
    
    print("\n" + DIVIDER)
    print("RESUMING GRAPH (Simulating User Approval)")
    print(DIVIDER)
    
    # We pass the required payload back to the wait_for_user_node
    resume_payload = {
        "plan_approved": True,
        "user_feedback": "",
        "subquestions": snapshot.values.get("subquestions", [])
    }
    
    for step in app.stream(Command(resume=resume_payload), config=config, stream_mode="updates"):
        for node_name, state_update in step.items():
            print(f"\n[{node_name.upper()}] state update:")
            
            # (Reuse printing logic here, or just keep it minimal)
            if not isinstance(state_update, dict):
                print(f"  Data: {truncate(str(state_update))}")
                continue

            if node_name == "context_enhancer":
                sr = state_update.get("search_results", [])
                if sr:
                    print(f"  subquestion : {sr[0].query}")
                    print(f"  chunks      : {len(sr[0].result)}")
            elif node_name == "synthesizer":
                report = state_update.get("final_report")
                if report:
                    print(f"  summary         : {truncate(report.summary, 200)}")
            else:
                 print(f"  (Node finished: {node_name})")

        final_state = step
        iter_count += 1

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
