import json
from pydantic import BaseModel
from typing import Literal, Optional
from app.openrouter import call_model_with_schema, model_used_ctx
from app.agent.state import ConversationalResponse, GraphState, TaskType
from app.agent.pipeline import trace_node

class RouterDecision(BaseModel):
    selected_tool: Literal["vqa", "segmentation", "change_detection", "fusion", "conversational"]
    reasoning: str

async def conversational_router_node(state: GraphState) -> GraphState:
    trace_node(state, "conversational_router")
    
    # Context
    history_str = json.dumps(state.image_context.get("chat_history", []))
    classifier_info = f"Classifier suggested: {state.inferred_task} (Scores: {state.classifier_scores})"
    missing = state.missing_inputs
    missing_str = f"Missing required inputs for {state.inferred_task}: {', '.join(missing)}" if missing else "All required inputs present."

    system_prompt = (
        "You are the central orchestrator for a remote sensing AI assistant.\n"
        "Your job is to decide which tool to execute based on the user's query, the chat history, and the classifier's suggestion.\n"
        "CRITICAL INSTRUCTION: You MUST select the classifier's suggested tool unless inputs are missing or the user is just making small talk (like saying 'hi').\n"
        "If a specific analysis is requested but inputs are missing, select 'conversational' to explain that you need them.\n"
        "Otherwise, select the appropriate analysis tool."
    )
    
    user_prompt = f"Chat History: {history_str}\n\nClassifier: {classifier_info}\nMissing Inputs: {missing_str}\n\nUser Query: {state.user_query}"

    try:
        decision, reasoning = await call_model_with_schema(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], 
            RouterDecision, 
            max_tokens=300, 
            temperature=0.1, 
            role="conversational_agent"
        )
        
        if decision.selected_tool == "conversational" and missing:
            state.needs_clarification = True
            
        state.mode = decision.selected_tool
        
        requires_pair = state.mode in {"change_detection", "fusion"}
        state.task_type = TaskType(
            kind=state.mode if state.mode != "conversational" else "vqa",
            requires_pair=requires_pair,
            requires_sar=(state.mode == "fusion")
        )

        state.task_routing_reason = f"Conversational router chose '{state.mode}'. Reasoning: {decision.reasoning}"
        if state.trace and reasoning:
            state.trace[-1].reasoning = reasoning
            
    except Exception as exc:
        state.errors.append({"node": "conversational_router", "error": str(exc), "recovered": True})
        state.mode = state.inferred_task if state.inferred_task in ["vqa", "segmentation", "change_detection", "fusion"] else "vqa"
        
    # Hard constraints are applied after model-based routing, including its fallback.
    from app.agent.registry import missing_inputs as required_inputs
    # The selected pair configuration defines the available specialist workflow.
    if state.image_context.get("before") and state.image_context.get("after"):
        state.mode = "change_detection"
    elif state.image_context.get("optical") and state.image_context.get("sar"):
        state.mode = "fusion"
    missing_required = required_inputs(state.mode, state.image_context)
    if missing_required:
        state.missing_inputs = missing_required
        state.needs_clarification = True
        state.mode = "conversational"
    state.task_type = TaskType(kind=state.mode if state.mode != "conversational" else "vqa",
                               requires_pair=state.mode in {"change_detection", "fusion"},
                               requires_sar=state.mode == "fusion")
    if not state.needs_clarification:
        state.inferred_task = state.mode
    state.task_routing_reason = f"Selected {state.mode}; input requirements checked against capability registry."
    return state

async def conversational_aggregator_node(state: GraphState) -> GraphState:
    trace_node(state, "conversational_aggregator")
    history_str = json.dumps(state.image_context.get("chat_history", []))
    
    if state.needs_clarification and state.missing_inputs:
        state.final_answer = "This analysis requires: " + ", ".join(state.missing_inputs) + ". Upload the missing observations and retry."
        return state

    tool_executed = state.mode
    # Keep image payloads and internal model text out of the synthesis prompt.
    public_output = {key: value for key, value in state.tool_result.items()
                     if key not in {"mask", "segment_mask", "change_mask", "internal_reasoning"}}
    tool_output = json.dumps(public_output) if public_output else "No tool output generated."
    
    if state.needs_clarification and state.missing_inputs:
        tool_output = f"I need the user to upload: {', '.join(state.missing_inputs)}"
    
    system_prompt = (
        "You are a helpful conversational remote sensing AI assistant.\n"
        "You have just executed a tool or analysis in the background. Your job is to present the results naturally to the user.\n"
        "If the tool returned an error or asked the user to 'click the region' (like in segmentation), gently tell the user.\n"
        "If the user is just saying hello, respond naturally.\n"
        "If inputs are missing, politely ask the user to provide them. "
        "Never invent measurements, confidence, or sensor properties. Preserve all limitations and tool errors. "
        "RGB difference is not a semantic change map. Optical and radar brightness are not directly comparable."
    )
    
    user_prompt = (
        f"Chat History: {history_str}\n\n"
        f"User Query: {state.user_query}\n\n"
        f"Tool Executed: {tool_executed}\n"
        f"Raw Tool Output: {tool_output}\n\n"
        "Please provide the final conversational response to the user."
    )

    try:
        result, reasoning = await call_model_with_schema([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ], ConversationalResponse, max_tokens=300, temperature=0.2, role="conversational_agent")
        
        state.model_used = model_used_ctx.get()
        state.final_answer = result.answer
        
        if state.trace and reasoning:
            state.trace[-1].reasoning = reasoning
            
    except Exception as exc:
        state.errors.append({"node": "conversational_aggregator", "error": str(exc), "recovered": True})
        state.final_answer = "I'm sorry, I couldn't synthesize the final response."
        
    return state
