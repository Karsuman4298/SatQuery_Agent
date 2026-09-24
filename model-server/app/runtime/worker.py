"""Optional Celery worker. Queue messages contain job IDs and owner scope only."""
import asyncio
from uuid import UUID
from celery import Celery
from app.config import settings
from app.runtime.contracts import Asset, Evidence, now

celery_app = Celery('satquery', broker=settings.runtime_queue_url)
celery_app.conf.update(task_serializer='json', accept_content=['json'], task_acks_late=True,
                       worker_prefetch_multiplier=1, task_soft_time_limit=900, task_time_limit=960)


@celery_app.task(name='satquery.process_job')
def process_job(owner, job_id):
    from app.runtime.api import runtime
    service = runtime()
    job = service.records.get(owner, 'job', job_id)
    if job['status'] == 'complete': return job
    job.update(status='running', started_at=now().isoformat())
    service.records.put(owner, 'job', job_id, job)
    try:
        if job['kind'] == 'ingestion':
            from app.runtime.ingestion import ingest
            asset = ingest(service.objects.get(job['source_uri']), job['filename'], owner,
                           job['metadata'], service.objects, service.records)
            job['asset_id'] = str(asset.asset_id)
        elif job['kind'] == 'index':
            asyncio.run(index_tiles(service, owner, job['asset_id']))
        else:
            raise ValueError('Unknown job type')
        job.update(status='complete', completed_at=now().isoformat())
    except Exception as exc:
        job.update(status='failed', error=type(exc).__name__, completed_at=now().isoformat())
        service.records.put(owner, 'job', job_id, job)
        raise
    service.records.put(owner, 'job', job_id, job)
    return job


async def index_tiles(service, owner, asset_id):
    """Caption-derived tile vectors, explicitly not raw SAR/optical image embeddings."""
    import base64
    from uuid import uuid5, NAMESPACE_URL
    from app.openrouter import call_model_with_schema, model_used_ctx
    from app.runtime.specialists import SpecialistOutput
    asset = Asset.model_validate(service.records.get(owner, 'asset', asset_id))
    for tile in asset.tiles:
        preview = base64.b64encode(service.objects.get(tile['storage_uri'])).decode()
        output, _ = await call_model_with_schema([
            {'role': 'system', 'content': 'Describe visible remote-sensing features in this tile as attributable claims, asset_index=0. Do not infer sensor, location, calibrated measurements, or dates. State uncertainty.'},
            {'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{preview}'}}]}
        ], SpecialistOutput, max_tokens=500, max_retries=1)
        text = ' '.join(claim.text for claim in output.claims)
        if not text: continue
        evidence = Evidence(evidence_id=uuid5(NAMESPACE_URL, f'{owner}:{tile["tile_id"]}'),
            asset_id=asset.asset_id, type='interpretation', text=text[:4000],
            bbox_pixel=tuple(tile['bbox_pixel']), score=None,
            model_name=model_used_ctx.get() or 'configured-vlm', model_version='caption-index-v1')
        await service.retrieval.index(owner, UUID(int=0), evidence, domain='asset')
