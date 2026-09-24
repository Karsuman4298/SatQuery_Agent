"""Versioned model-server API; the existing /agent endpoint remains compatible."""
from __future__ import annotations
import hmac
from datetime import datetime
from rasterio.errors import RasterioError
from functools import lru_cache
from typing import Literal
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from app.config import settings
from app.runtime.contracts import Query, Execution, Asset
from app.runtime.storage import ObjectStore, MetadataStore
from app.runtime.retrieval import Retrieval
from app.runtime.engine import Runtime
from app.runtime.ingestion import ingest
from app.runtime.policies import CAPABILITIES
from uuid import UUID

router = APIRouter(prefix='/v2', tags=['asset-reference runtime'])


@lru_cache(maxsize=1)
def runtime():
    records = MetadataStore(settings.runtime_database_url)
    objects = ObjectStore(settings.runtime_object_dir, settings.runtime_s3_endpoint, settings.runtime_s3_bucket,
                          settings.runtime_s3_access_key, settings.runtime_s3_secret_key)
    retrieval = Retrieval(records, settings.runtime_qdrant_url, settings.ollama_base_url)
    return Runtime(records, objects, retrieval)


def owner(x_satquery_key: str | None = Header(None), x_satquery_owner: str | None = Header(None)):
    # The gateway asserts owner identity only after authenticating the user. A caller
    # without a configured gateway key cannot impersonate another local owner.
    if settings.runtime_gateway_key:
        if not x_satquery_key or not hmac.compare_digest(x_satquery_key, settings.runtime_gateway_key):
            raise HTTPException(401, 'A valid gateway service key is required.')
        if not x_satquery_owner or not 1 <= len(x_satquery_owner) <= 128:
            raise HTTPException(422, 'Gateway must supply a bounded owner ID.')
        return x_satquery_owner
    if x_satquery_owner and x_satquery_owner != 'local':
        raise HTTPException(403, 'Unconfigured local mode cannot assert other owners.')
    return 'local'


@router.get('/capabilities')
def capabilities(scope=Depends(owner)):
    return {'tools': CAPABILITIES, 'adaptation': 'Training and held-out evaluation required; no trained adapter is bundled.',
            'storage_profile': 'postgres' if settings.runtime_database_url.startswith('postgres') else 'local',
            'retrieval': 'hybrid' if settings.runtime_qdrant_url else 'lexical',
            'limits': {'max_upload_bytes': 50*1024*1024, 'max_pixels': 100_000_000, 'max_retries': 2}}


@router.post('/assets', response_model=Asset, status_code=201)
async def upload(file: UploadFile = File(...), modality: Literal['optical', 'multispectral', 'sar'] = Form(...),
    benchmark: Literal['VRSBench', 'RSVQA', 'CDVQA', 'BigEarthNet.txt'] | None = Form(None),
    acquisition_time: datetime | None = Form(None), sensor: str | None = Form(None), scope=Depends(owner)):
    data = bytearray()
    try:
        while chunk := await file.read(1024*1024):
            data.extend(chunk)
            if len(data) > 50*1024*1024: raise HTTPException(413, 'File exceeds 50 MB.')
        service = runtime()
        asset = await run_in_threadpool(ingest, bytes(data), file.filename or '', scope,
            {'modality': modality, 'benchmark': benchmark, 'acquisition_time': acquisition_time,
             'sensor': sensor}, service.objects, service.records)
        return asset
    except (ValueError, OSError, RasterioError) as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        await file.close()


@router.get('/assets/{asset_id}', response_model=Asset)
def asset(asset_id: UUID, scope=Depends(owner)):
    try: return runtime().records.get(scope, 'asset', str(asset_id))
    except KeyError: raise HTTPException(404, 'Asset not found.')


@router.get('/assets/{asset_id}/preview')
def preview(asset_id: UUID, scope=Depends(owner)):
    record = asset(asset_id, scope)
    return Response(runtime().objects.get(record['preview_uri']), media_type='image/png')


@router.post('/query', response_model=Execution)
async def query(request: Query, scope=Depends(owner)):
    try:
        return await runtime().run(scope, request)
    except KeyError as exc: raise HTTPException(404, 'An asset was not found in this owner scope.') from exc
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    except TimeoutError as exc: raise HTTPException(504, 'Specialist execution timed out.') from exc
    except Exception as exc: raise HTTPException(503, 'Specialist or storage unavailable. Inspect the persisted execution trace.') from exc


@router.get('/executions/{execution_id}', response_model=Execution)
def execution(execution_id: UUID, scope=Depends(owner)):
    try: return runtime().records.get(scope, 'execution', str(execution_id))
    except KeyError: raise HTTPException(404, 'Execution not found.')


@router.get('/threads/{thread_id}/executions')
def history(thread_id: UUID, scope=Depends(owner)):
    return runtime().records.list(scope, 'execution', str(thread_id), limit=50)


@router.get('/executions/{execution_id}/masks/{evidence_id}')
def mask(execution_id: UUID, evidence_id: UUID, scope=Depends(owner)):
    record = execution(execution_id, scope)
    item = next((item for item in record['evidence'] if item['evidence_id'] == str(evidence_id) and item.get('mask_uri')), None)
    if not item: raise HTTPException(404, 'Mask not found.')
    return Response(runtime().objects.get(item['mask_uri']), media_type='image/png')


def enqueue(scope, job):
    from uuid import uuid4
    from app.runtime.contracts import now
    if not settings.runtime_queue_url:
        raise HTTPException(503, 'Configure the job broker and worker for asynchronous processing.')
    job_id = str(uuid4())
    job.update(job_id=job_id, owner=scope, status='queued', created_at=now().isoformat())
    service = runtime()
    service.records.put(scope, 'job', job_id, job)
    try:
        from app.runtime.worker import process_job
        process_job.delay(scope, job_id)
    except Exception as exc:
        job.update(status='failed', error='Queue publication failed')
        service.records.put(scope, 'job', job_id, job)
        raise HTTPException(503, 'Could not enqueue the job. Check the broker.') from exc
    return job


@router.post('/ingestions', status_code=202)
async def queue_ingestion(file: UploadFile = File(...), modality: Literal['optical', 'multispectral', 'sar'] = Form(...),
    benchmark: Literal['VRSBench', 'RSVQA', 'CDVQA', 'BigEarthNet.txt'] | None = Form(None),
    acquisition_time: datetime | None = Form(None), sensor: str | None = Form(None), scope=Depends(owner)):
    if not settings.runtime_queue_url:
        raise HTTPException(503, 'Configure a worker, or use synchronous /v2/assets ingestion.')
    data = bytearray()
    try:
        while chunk := await file.read(1024*1024):
            data.extend(chunk)
            if len(data) > 50*1024*1024: raise HTTPException(413, 'File exceeds 50 MB.')
        if not data: raise HTTPException(422, 'File is empty.')
        from hashlib import sha256
        uri = await run_in_threadpool(runtime().objects.put, bytes(data), 'pending/' + sha256(scope.encode()).hexdigest()[:24], 'upload')
        return await run_in_threadpool(enqueue, scope, {'kind': 'ingestion', 'source_uri': uri, 'filename': file.filename,
            'metadata': {'modality': modality, 'benchmark': benchmark, 'sensor': sensor,
                         'acquisition_time': acquisition_time.isoformat() if acquisition_time else None}})
    finally:
        await file.close()


@router.post('/assets/{asset_id}/index', status_code=202)
def queue_index(asset_id: UUID, scope=Depends(owner)):
    asset(asset_id, scope)
    return enqueue(scope, {'kind': 'index', 'asset_id': str(asset_id)})


@router.get('/jobs/{job_id}')
def job(job_id: UUID, scope=Depends(owner)):
    try: return runtime().records.get(scope, 'job', str(job_id))
    except KeyError: raise HTTPException(404, 'Job not found.')
