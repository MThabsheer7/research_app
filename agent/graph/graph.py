from langgraph.graph import StateGraph, START, END
from agent.graph.state import ResearchState
from agent.graph.nodes.planner import planner_node, route_planner
from agent.graph.nodes.decomposer import decomposer_node
from agent.graph.nodes.context_enhancer import context_enhancer_node
from agent.graph.nodes.synthesizer import synthesizer_node, route_synthesizer
from agent.graph.edges import dispatch_searchers

import os
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

MAX_ITERATIONS = 5

research_graph = StateGraph(ResearchState)

# Add the nodes
research_graph.add_node("planner", planner_node)
research_graph.add_node("decomposer", decomposer_node)
research_graph.add_node("context_enhancer", context_enhancer_node)
research_graph.add_node("synthesizer", synthesizer_node)

# Add the edges
research_graph.add_edge(START, "planner")
research_graph.add_conditional_edges(
    "planner",
    route_planner,
    {
        "complex": "decomposer",
        "simple": "synthesizer"
    }
)
# Fan-out: one context_enhancer per subquestion, dispatched via Send()
research_graph.add_conditional_edges("decomposer", dispatch_searchers, ["context_enhancer"])
research_graph.add_edge("context_enhancer", "synthesizer")
research_graph.add_conditional_edges(
    "synthesizer",
    route_synthesizer,
    {
        "retry": "planner",
        "done": END
    }
)

# ── Persistence ───────────────────────────────────────────────────────────────
# SqliteSaver writes a checkpoint after every node completes.
# check_same_thread=False is required for use across FastAPI request threads.
_DB_PATH = os.environ.get("CHECKPOINT_DB", "data/checkpoints.db")
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
_checkpointer = SqliteSaver(_conn)

# Compile the graph with the SQLite checkpointer
research_app = research_graph.compile(checkpointer=_checkpointer)