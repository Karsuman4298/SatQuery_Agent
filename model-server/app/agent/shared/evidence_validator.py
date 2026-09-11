from app.agent.state import GraphState
from app.agent.pipeline import validate_claims, trace_node, judge_claims as base_judge_claims

def evidence_node(state: GraphState) -> GraphState:
    trace_node(state, "evidence_validator")
    return validate_claims(state)

async def judge_claims(state: GraphState) -> GraphState:
    trace_node(state, "evidence_judge")
    return await base_judge_claims(state)
