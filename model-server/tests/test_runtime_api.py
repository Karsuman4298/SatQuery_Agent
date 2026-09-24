import io
import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.runtime import api
from app.runtime.storage import MetadataStore, ObjectStore
from app.runtime.retrieval import Retrieval
from app.runtime.engine import Runtime
from app.runtime.contracts import Evidence


@pytest.fixture
def client(tmp_path, monkeypatch):
    records = MetadataStore(f'sqlite:///{tmp_path}/db.sqlite')
    objects = ObjectStore(str(tmp_path / 'objects'))
    async def fake(plan, assets, query, objects, context, feedback):
        return [Evidence(asset_id=assets[0].asset_id, type='observation', text='Fixture scene', model_name='test', model_version='1')], [], []
    service = Runtime(records, objects, Retrieval(records), specialist=fake)
    monkeypatch.setattr(api, 'runtime', lambda: service)
    monkeypatch.setattr(api.settings, 'runtime_gateway_key', 'test-key')
    app = FastAPI(); app.include_router(api.router)
    return TestClient(app)


def upload(client, owner='alice'):
    buffer = io.BytesIO(); Image.new('RGB', (16, 16), (20, 40, 80)).save(buffer, format='PNG')
    return client.post('/v2/assets', headers={'X-Satquery-Key': 'test-key', 'X-Satquery-Owner': owner},
        files={'file': ('scene.png', buffer.getvalue(), 'image/png')},
        data={'modality': 'optical', 'benchmark': 'VRSBench'})


def test_upload_query_trace_and_ownership(client):
    response = upload(client)
    assert response.status_code == 201, response.text
    asset = response.json(); headers = {'X-Satquery-Key': 'test-key', 'X-Satquery-Owner': 'alice'}
    preview = client.get(f'/v2/assets/{asset["asset_id"]}/preview', headers=headers)
    assert preview.status_code == 200 and preview.headers['content-type'] == 'image/png'
    response = client.post('/v2/query', headers=headers, json={'query': 'Describe this scene', 'asset_ids': [asset['asset_id']]})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['status'] == 'complete' and result['plan']['task'] == 'caption'
    assert result['confidence'] is None and result['evidence'][0]['verified'] is False
    assert client.get('/v2/executions/' + result['execution_id'], headers=headers).status_code == 200
    headers['X-Satquery-Owner'] = 'bob'
    assert client.get('/v2/assets/' + asset['asset_id'], headers=headers).status_code == 404
    assert client.get('/v2/executions/' + result['execution_id'], headers=headers).status_code == 404


def test_auth_invalid_upload_and_payload(client):
    assert client.get('/v2/capabilities').status_code == 401
    headers = {'X-Satquery-Key': 'test-key', 'X-Satquery-Owner': 'alice'}
    response = client.post('/v2/assets', headers=headers, files={'file': ('broken.tif', b'broken', 'image/tiff')}, data={'modality': 'optical'})
    assert response.status_code == 422
    response = client.post('/v2/query', headers=headers, json={'query': 'Describe', 'asset_ids': [], 'max_retries': 100})
    assert response.status_code == 422


def test_local_scope_cannot_be_impersonated(client, monkeypatch):
    monkeypatch.setattr(api.settings, 'runtime_gateway_key', '')
    assert client.get('/v2/capabilities', headers={'X-Satquery-Owner': 'someone-else'}).status_code == 403
    assert client.get('/v2/capabilities').status_code == 200
