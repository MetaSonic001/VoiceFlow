import tempfile
import os
import io
import pytest
from fastapi.testclient import TestClient


class DummyMinioClient:
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def put_object(self, bucket_name, object_name, data, length, content_type=None):
        target = os.path.join(self.storage_dir, object_name.replace('/', '_'))
        with open(target, 'wb') as f:
            if hasattr(data, 'read'):
                f.write(data.read())
            else:
                f.write(data)

    def bucket_exists(self, bucket_name):
        return True


@pytest.fixture()
def client(monkeypatch, tmp_path):
    # Import the app and monkeypatch the minio helper to return a dummy client
    from backend.main import app
    storage = tmp_path / 'minio'
    dummy = DummyMinioClient(str(storage))

    def get_minio_client():
        return dummy

    monkeypatch.setattr('backend.main.get_minio_client', get_minio_client)
    with TestClient(app) as c:
        yield c


def test_upload_and_list(client):
    # get guest token
    r = client.post('/auth/guest')
    assert r.status_code == 200
    token = r.json().get('access_token')

    headers = {'Authorization': f'Bearer {token}'}

    # create tenant
    r = client.post('/tenants', json={'name': 't1'})
    assert r.status_code == 200
    tenant_id = r.json()['id']

    # create agent
    r = client.post('/agents', json={'tenant_id': tenant_id, 'name': 'a1'})
    assert r.status_code == 200
    agent_id = r.json()['id']

    # upload a small file
    data = {'file': ('hello.txt', io.BytesIO(b'hello world'), 'text/plain')}
    r = client.post(f'/upload/{tenant_id}/{agent_id}', files=data, headers=headers)
    assert r.status_code == 200
    payload = r.json()
    assert 'id' in payload

    # list documents
    r = client.get(f'/documents/{agent_id}')
    assert r.status_code == 200
    docs = r.json().get('documents', [])
    assert len(docs) >= 1
