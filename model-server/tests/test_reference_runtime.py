"""Offline contract/integration tests with a declared fake specialist, never fake production answers."""
import asyncio
import io
import json
from datetime import datetime, timezone
from uuid import uuid4
import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from PIL import Image
from app.runtime.contracts import Asset, Query, Evidence
from app.runtime.storage import MetadataStore, ObjectStore
from app.runtime.ingestion import ingest
from app.runtime.policies import build_plan
from app.runtime.retrieval import Retrieval, lexical_rank, rrf
from app.runtime.engine import Runtime
from app.runtime.specialists import verify


@pytest.fixture
def stores(tmp_path):
    return MetadataStore(f'sqlite:///{tmp_path}/metadata.db'), ObjectStore(str(tmp_path / 'objects'))


def raster(value=80):
    with MemoryFile() as mem:
        with mem.open(driver='GTiff', width=40, height=24, count=3, dtype='uint8',
                      crs='EPSG:32632', transform=from_origin(500000, 4600000, 10, 10)) as dst:
            dst.write(np.full((3, 24, 40), value, dtype='uint8'))
        return mem.read()


def add(stores, owner='alice', value=80, **metadata):
    records, objects = stores
    return ingest(raster(value), 'scene.tif', owner, {'modality': 'optical', **metadata}, objects, records)


def test_ingestion_preserves_pixels_and_deduplicates(stores):
    asset = add(stores)
    assert add(stores).asset_id == asset.asset_id
    assert stores[1].get(asset.storage_uri) == raster()
    assert len(asset.tiles) == 1
    assert all(-180 <= value <= 180 for value in asset.bbox_geo)
    assert Image.open(io.BytesIO(stores[1].get(asset.preview_uri))).size == (40, 24)
    other_owner = add(stores, owner='bob')
    assert other_owner.asset_id != asset.asset_id
    with pytest.raises(KeyError): stores[0].get('bob', 'asset', str(asset.asset_id))


def test_invalid_format_and_benchmark_enforced(stores):
    with pytest.raises(ValueError, match='source'):
        ingest(b'x', 'scene.png', 'alice', {'modality': 'optical'}, stores[1], stores[0])
    with pytest.raises(ValueError, match='extension'):
        ingest(raster(), 'scene.png', 'alice', {'modality': 'optical', 'benchmark': 'VRSBench'}, stores[1], stores[0])
    with pytest.raises(ValueError): stores[1].get('../outside')


def test_plan_pair_requirements(stores):
    a = add(stores, acquisition_time='2024-01-01T00:00:00Z')
    b = add(stores, value=90, acquisition_time='2025-01-01T00:00:00Z')
    query = Query(query='What changed?', asset_ids=[a.asset_id, b.asset_id])
    assert build_plan(query, [a, b]).task == 'change'
    b.transform[2] += 10
    with pytest.raises(ValueError, match='pixel grids'): build_plan(query, [a, b])
    with pytest.raises(ValueError, match='2 image'):
        build_plan(Query(query='What changed?', asset_ids=[a.asset_id]), [a])


def test_fusion_requires_sensor_order(stores):
    optical = add(stores)
    sar = add(stores, value=100, modality='sar')
    query = Query(query='Identify water', asset_ids=[optical.asset_id, sar.asset_id])
    assert build_plan(query, [optical, sar]).task == 'fusion'
    with pytest.raises(ValueError, match='first'):
        build_plan(query, [sar, optical])


def test_structural_verifier_rejects_invalid_geometry(stores):
    asset = add(stores)
    bad = Evidence(asset_id=asset.asset_id, text='Claim', type='observation',
                   bbox_pixel=(0, 0, 1000, 1000), model_name='test', model_version='1')
    good = bad.model_copy(update={'bbox_pixel': (1, 1, 5, 5)})
    evidence, conflicts = verify([bad, good], [asset])
    assert len(evidence) == 1 and conflicts
    assert evidence[0].bbox_geo is not None
    assert evidence[0].verified is False


def test_runtime_bounded_retry_and_persistence(stores):
    asset = add(stores)
    calls = []
    async def specialist(plan, assets, query, objects, context, feedback):
        calls.append(feedback)
        box = (0, 0, 1000, 1000) if len(calls) == 1 else (1, 1, 5, 5)
        return [Evidence(asset_id=asset.asset_id, text='Test claim', type='observation',
                         bbox_pixel=box, model_name='test', model_version='1')], [], []
    runtime = Runtime(*stores, Retrieval(stores[0]), specialist=specialist)
    query = Query(query='Describe this scene', asset_ids=[asset.asset_id], max_retries=1)
    result = asyncio.run(runtime.run('alice', query))
    assert result.status == 'complete' and result.attempts == 2
    assert 'evidence:' in result.answer
    assert result.confidence is None
    stored = stores[0].get('alice', 'execution', str(result.execution_id))
    assert stored['status'] == 'complete'
    assert 'base64' not in json.dumps(stored)
    assert len(stores[0].list('alice', 'message', str(query.thread_id))) == 2
    assert stores[0].list('alice', 'memory') == []


def test_retry_never_exceeds_bound(stores):
    asset = add(stores)
    async def empty(*args): return [], [], ['Unsupported claim']
    runtime = Runtime(*stores, Retrieval(stores[0]), specialist=empty)
    result = asyncio.run(runtime.run('alice', Query(query='Describe image', asset_ids=[asset.asset_id], max_retries=2)))
    assert result.attempts == 3 and result.status == 'uncertain'
    assert not result.evidence


def test_failures_are_persisted_and_not_successful(stores):
    asset = add(stores)
    async def unavailable(*args): raise RuntimeError('offline')
    runtime = Runtime(*stores, Retrieval(stores[0]), specialist=unavailable)
    query = Query(query='Describe scene', asset_ids=[asset.asset_id])
    with pytest.raises(RuntimeError): asyncio.run(runtime.run('alice', query))
    record = stores[0].list('alice', 'execution', str(query.thread_id))[0]
    assert record['status'] == 'failed' and record['trace'][-1]['status'] == 'failed'


def test_memory_scoping_and_promotion(stores):
    asset = add(stores)
    thread = uuid4()
    retrieval = Retrieval(stores[0])
    evidence = Evidence(asset_id=asset.asset_id, text='Water surrounds the fields', type='observation', model_name='test', model_version='1')
    asyncio.run(retrieval.index('alice', thread, evidence))
    matches, _ = asyncio.run(retrieval.search('alice', uuid4(), [asset.asset_id], 'water'))
    assert not matches
    asyncio.run(retrieval.index('alice', thread, evidence, promoted=True))
    matches, _ = asyncio.run(retrieval.search('alice', uuid4(), [asset.asset_id], 'water'))
    assert len(matches) == 1
    matches, _ = asyncio.run(retrieval.search('bob', thread, [asset.asset_id], 'water'))
    assert not matches


def test_rrf_and_lexical_ranking():
    a, b = {'evidence_id': 'a', 'text': 'river water'}, {'evidence_id': 'b', 'text': 'buildings road'}
    assert lexical_rank('water', [a, b]) == [a]
    assert rrf([a, b], [a])[0] == a
