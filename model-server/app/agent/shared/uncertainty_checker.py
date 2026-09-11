from app.agent.state import GraphState
from app.agent.pipeline import calculate_uncertainty, trace_node

def uncertainty_node(state: GraphState) -> GraphState:
    trace_node(state, "uncertainty_checker")
    return calculate_uncertainty(state)
