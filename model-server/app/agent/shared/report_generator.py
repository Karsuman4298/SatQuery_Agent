from app.agent.state import GraphState
from app.agent.pipeline import render_report, trace_node

def report_node(state: GraphState) -> GraphState:
    trace_node(state, "report_generator")
    result = state.tool_result
    
    if state.mode == "vqa":
        answer = result.get("answer", "")
    elif state.mode == "change_detection":
        answer = f"{result.get('summary', '')}\n\n**Change Extent:** {result.get('change_pct', 0):.1f}% of the scene area shows pixel-level difference."
    elif state.mode == "fusion":
        answer = f"{result.get('verification_result', '')}\n\n**Computed agreement indicator:** {result.get('agreement_pct', 0):.1f}%"
    elif state.mode == "segmentation":
        if "answer" in result:
            answer = result["answer"]
        else:
            caption = result.get('caption', 'a segmented region')
            conf = result.get('confidence', 0.0)
            answer = f"**Segmented Region:** {caption}\n**Confidence Score:** {conf:.2f}\n\nGenerated based on your query: {state.user_query}"
    elif state.mode == "conversational":
        answer = result.get("answer", "")
    else:
        answer = ""
        
    return render_report(state, answer)

def error_node(state: GraphState) -> GraphState:
    trace_node(state, "error_responder")
    if state.needs_clarification:
        state.final_answer = state.clarification_message
    else:
        state.final_answer = "Unable to analyze the input: " + "; ".join(state.validation_errors)
    return state
