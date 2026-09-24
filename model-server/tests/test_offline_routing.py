import asyncio
from app.agent.pipeline import new_state, validate_input
from app.agent.modes.conversational import conversational_router_node, conversational_aggregator_node


def test_missing_embedding_service_preserves_workflow(monkeypatch):
    async def unavailable(): raise ConnectionError('offline')
    monkeypatch.setattr('app.agent.pipeline.get_classifier', unavailable)
    state = asyncio.run(validate_input(new_state('Compare these dates', {'before': 'a', 'after': 'b'}, 'change_detection')))
    assert state.inferred_task == 'change_detection'
    assert state.classifier_confidence == 0
    assert state.errors[-1]['recovered'] is True


def test_router_cannot_execute_pair_tool_without_inputs(monkeypatch):
    from app.agent.modes.conversational import RouterDecision
    async def route(*args, **kwargs):
        return RouterDecision(selected_tool='fusion', reasoning='fixture'), None
    monkeypatch.setattr('app.agent.modes.conversational.call_model_with_schema', route)
    state = new_state('Combine radar and optical', {'image': 'a'})
    state = asyncio.run(conversational_router_node(state))
    assert state.needs_clarification
    assert state.mode == 'conversational'
    state = asyncio.run(conversational_aggregator_node(state))
    assert 'optical' in state.final_answer and 'sar' in state.final_answer


def test_pair_configuration_cannot_be_discarded_by_router(monkeypatch):
    from app.agent.modes.conversational import RouterDecision
    async def route(*args, **kwargs):
        return RouterDecision(selected_tool='vqa', reasoning='fixture'), None
    monkeypatch.setattr('app.agent.modes.conversational.call_model_with_schema', route)
    state = new_state('What changed?', {'image': 'a', 'before': 'a', 'after': 'b'})
    state = asyncio.run(conversational_router_node(state))
    assert state.mode == 'change_detection'
    assert state.task_type.kind == 'change_detection'
