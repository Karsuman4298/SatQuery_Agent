"""Reference-only LangGraph runtime with bounded retries and durable audit records."""
from __future__ import annotations
import asyncio
import time
from typing import TypedDict
from langgraph.graph import START, END, StateGraph
from app.runtime.contracts import Asset, Query, Execution, Trace, now
from app.runtime.policies import build_plan
from app.runtime.specialists import execute_specialist, verify


class WorkingState(TypedDict):
    owner: str
    request: Query
    execution: Execution
    context: list[dict]
    retry: bool


class Runtime:
    def __init__(self, records, objects, retrieval, specialist=execute_specialist):
        self.records, self.objects, self.retrieval = records, objects, retrieval
        self.specialist = specialist
        graph = StateGraph(WorkingState)
        for name in ('plan', 'retrieve', 'execute', 'verify', 'finalize'):
            graph.add_node(name, getattr(self, name))
        graph.add_edge(START, 'plan')
        graph.add_edge('plan', 'retrieve')
        graph.add_edge('retrieve', 'execute')
        graph.add_edge('execute', 'verify')
        graph.add_conditional_edges('verify', lambda state: 'execute' if state['retry'] else 'finalize',
                                    {'execute': 'execute', 'finalize': 'finalize'})
        graph.add_edge('finalize', END)
        self.graph = graph.compile()

    def assets(self, state):
        return [Asset.model_validate(self.records.get(state['owner'], 'asset', str(key))) for key in state['request'].asset_ids]

    def save(self, state):
        execution = state['execution']
        self.records.put(state['owner'], 'execution', str(execution.execution_id), execution.model_dump(mode='json'), str(execution.thread_id))

    async def plan(self, state):
        started = time.monotonic()
        execution = state['execution']
        execution.plan = build_plan(state['request'], self.assets(state))
        execution.warnings.extend(execution.plan.limitations)
        execution.trace.append(Trace(stage='validate_and_plan', duration_ms=round((time.monotonic()-started)*1000),
            parameters=execution.plan.model_dump(mode='json')))
        self.save(state)
        return state

    async def retrieve(self, state):
        started = time.monotonic()
        query, execution = state['request'], state['execution']
        context, warnings = await self.retrieval.search(state['owner'], query.thread_id, query.asset_ids, query.query)
        # Bound conversation to the last 8 messages; no raw imagery enters working memory.
        messages = self.records.list(state['owner'], 'message', str(query.thread_id), limit=8)
        state['context'] = context + [{'conversation': row['content'], 'role': row['role']} for row in reversed(messages)]
        execution.warnings.extend(warnings)
        execution.trace.append(Trace(stage='retrieve_memory', duration_ms=round((time.monotonic()-started)*1000),
            parameters={'top_k': 5, 'message_limit': 8}, output_ids=[row['evidence_id'] for row in context]))
        self.save(state)
        return state

    async def execute(self, state):
        started = time.monotonic()
        execution = state['execution']
        execution.attempts += 1
        evidence, warnings, conflicts = await self.specialist(execution.plan, self.assets(state), state['request'],
            self.objects, state['context'], execution.conflicts)
        execution.evidence = evidence
        execution.warnings.extend(warnings)
        execution.conflicts = conflicts
        execution.trace.append(Trace(stage=execution.plan.tool, duration_ms=round((time.monotonic()-started)*1000),
            parameters={**execution.plan.parameters, 'attempt': execution.attempts},
            output_ids=[str(item.evidence_id) for item in evidence]))
        self.save(state)
        return state

    async def verify(self, state):
        execution = state['execution']
        execution.evidence, conflicts = verify(execution.evidence, self.assets(state))
        execution.conflicts.extend(conflicts)
        if not execution.evidence: execution.conflicts.append('No attributable evidence was returned.')
        # One controlled loop. No unbounded autonomous tool execution.
        state['retry'] = bool(execution.conflicts) and execution.attempts <= state['request'].max_retries
        execution.trace.append(Trace(stage='verify', status='warning' if execution.conflicts else 'complete',
            parameters={'will_retry': state['retry'], 'semantic_ground_truth_verified': False},
            detail='; '.join(execution.conflicts) or 'Asset references and geometry passed structural validation.'))
        self.save(state)
        return state

    async def finalize(self, state):
        query, execution = state['request'], state['execution']
        execution.status = 'uncertain' if execution.conflicts or not execution.evidence else 'complete'
        # Generate the displayed answer from attributable records, never uncited free text.
        lines = [f'{item.text} [evidence:{item.evidence_id}]' for item in execution.evidence]
        execution.answer = '\n\n'.join(lines) if lines else 'The available observations do not support a reliable answer.'
        if execution.conflicts:
            execution.answer += '\n\nUnresolved evidence issues: ' + '; '.join(execution.conflicts)
        execution.confidence = None  # Model self-scores are not an aggregate calibrated probability.
        execution.warnings = list(dict.fromkeys(execution.warnings + ['Evidence was structurally checked, not independently verified against ground truth.']))
        for item in execution.evidence:
            # Promotion is opt-in, only for completed runs. Prior claims remain unverified claims.
            try:
                await self.retrieval.index(state['owner'], query.thread_id, item,
                    promoted=query.promote_memory and execution.status == 'complete')
            except Exception:
                execution.warnings.append('Evidence persisted; semantic indexing failed and can be retried.')
        timestamp = now().isoformat()
        for position, (role, content) in enumerate([('user', query.query), ('assistant', execution.answer)]):
            self.records.put(state['owner'], 'message', f'{timestamp}:{execution.execution_id}:{position}',
                {'role': role, 'content': content, 'execution_id': str(execution.execution_id), 'created_at': timestamp}, str(query.thread_id))
        execution.completed_at = now()
        execution.trace.append(Trace(stage='persist', output_ids=[str(execution.execution_id)]))
        self.save(state)
        return state

    async def run(self, owner, query):
        execution = Execution(owner=owner, thread_id=query.thread_id, query=query.query)
        state = WorkingState(owner=owner, request=query, execution=execution, context=[], retry=False)
        self.save(state)
        try:
            result = await asyncio.wait_for(self.graph.ainvoke(state), timeout=170)
            return result['execution']
        except (Exception, asyncio.CancelledError) as exc:
            execution.status = 'failed'
            execution.completed_at = now()
            execution.answer = 'Execution failed. No successful analysis is claimed.'
            execution.trace.append(Trace(stage='error', status='failed', detail=type(exc).__name__))
            self.save(state)
            raise
