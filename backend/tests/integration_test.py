import os
import io
import asyncio
from fastapi.testclient import TestClient

# Make sure we import the backend app
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app
from backend.db import _ensure_engine_and_maker, _engine
from backend.models import Base


def setup_test_db():
    # Use a local sqlite DB for tests
    os.environ['BACKEND_DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'
    _ensure_engine_and_maker()
    async def _create():
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_create())


def test_upload_and_db_entry(monkeypatch):
    setup_test_db()

    # Mock MinIO client used by upload_file/get_minio_client
    class DummyMinio:
        def __init__(self):
            self.storage = {}

        def bucket_exists(self, bucket):
            return True

        def put_object(self, bucket, dest_path, fileobj, length, part_size):
            # read content
            fileobj.seek(0)
            content = fileobj.read()
            self.storage[dest_path] = content
            return True

        def get_object(self, bucket, obj):
            from io import BytesIO
            data = self.storage.get(obj)
            if data is None:
                raise FileNotFoundError()
            return BytesIO(data)

    dm = DummyMinio()
    monkeypatch.setattr('backend.minio_helper.get_minio_client', lambda: dm)
    monkeypatch.setattr('backend.minio_helper.ensure_bucket', lambda c=None: True)

    client = TestClient(app)

    # Create a tenant and agent
    r = client.post('/tenants', json={'name': 'TestCo'})
    assert r.status_code == 200
    tenant_id = r.json()['id']

    r = client.post('/agents', json={'tenant_id': tenant_id, 'name': 'support_bot'})
    assert r.status_code == 200
    agent_id = r.json()['id']

    # Upload a small text file
    files = {'file': ('sample.txt', io.BytesIO(b'hello world'), 'text/plain')}
    r = client.post(f'/upload/{tenant_id}/{agent_id}', files=files)
    assert r.status_code == 200
    data = r.json()
    assert 'id' in data and 'file_path' in data

    # Ensure the file was put into our dummy MinIO storage
    assert data['file_path'].startswith('tenants/')

    # Check documents list
    r = client.get(f'/documents/{agent_id}')
    assert r.status_code == 200
    docs = r.json().get('documents', [])
    assert len(docs) >= 1
