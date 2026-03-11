from langgraph.graph import StateGraph, START, END
from agent.graph.state import ResearchState
from agent.graph.nodes.planner import planner_node, route_planner
from agent.graph.nodes.human_interact import wait_for_user_node, route_after_interaction
from agent.graph.nodes.context_enhancer import context_enhancer_node
from agent.graph.nodes.synthesizer import synthesizer_node, route_synthesizer



MAX_ITERATIONS = 5

research_graph = StateGraph(ResearchState)

# Add the nodes
research_graph.add_node("planner", planner_node)
research_graph.add_node("wait_for_user", wait_for_user_node)
research_graph.add_node("context_enhancer", context_enhancer_node)
research_graph.add_node("synthesizer", synthesizer_node)

# Add the edges
research_graph.add_edge(START, "planner")
research_graph.add_conditional_edges(
    "planner",
    route_planner,
    {
        "wait_for_user": "wait_for_user",
        "synthesizer": "synthesizer"
    }
)
# After user interact, we either dispatch searchers or go back to planner
research_graph.add_conditional_edges(
    "wait_for_user", 
    route_after_interaction, 
    ["context_enhancer", "planner"]
)
research_graph.add_edge("context_enhancer", "synthesizer")
research_graph.add_conditional_edges(
    "synthesizer",
    route_synthesizer,
    {
        "retry": "planner",
        "done": END
    }
)

# Compile the graph without checkpointer for static use. 
# We will inject AsyncSqliteSaver dynamically at runtime in the API layer.
research_app = research_graph.compile()