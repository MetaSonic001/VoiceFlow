import os
import io
import asyncio
import uuid
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Set test database URL before importing anything else
os.environ['BACKEND_DATABASE_URL'] = 'sqlite+aiosqlite:///./test.db'

# Make sure we import the backend app
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app
from backend.db import _ensure_engine_and_maker, _engine
from backend.models import Base, Tenant, Agent, AgentConfiguration, Document


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Set up test database for each test."""
    # Database URL is already set to SQLite at module level
    _ensure_engine_and_maker()

    # Drop all tables and recreate
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def mock_minio():
    """Mock MinIO client for testing."""
    class DummyMinio:
        def __init__(self):
            self.storage = {}
            self.buckets = set()

        def bucket_exists(self, bucket):
            return bucket in self.buckets

        def make_bucket(self, bucket):
            self.buckets.add(bucket)

        def put_object(self, bucket, key, fileobj, length=-1, part_size=10*1024*1024):
            # Read the file content
            if hasattr(fileobj, 'read'):
                content = fileobj.read()
            else:
                content = fileobj
            self.storage[f"{bucket}/{key}"] = content
            return None

        def get_object(self, bucket, key):
            from io import BytesIO
            content = self.storage.get(f"{bucket}/{key}", b"")
            if isinstance(content, str):
                content = content.encode('utf-8')
            return BytesIO(content)

    mock_client = DummyMinio()
    mock_client.buckets.add('voiceflow')  # Pre-create the bucket

    with patch('backend.minio_helper.get_minio_client', return_value=mock_client):
        yield mock_client
@pytest.fixture
def client(mock_minio):
    """Test client with mocked dependencies."""
    with patch('backend.minio_helper.get_minio_client', return_value=mock_minio), \
         patch('backend.minio_helper.ensure_bucket', return_value=True), \
         patch('backend.minio_helper.upload_file') as mock_upload:

        # Mock upload_file to use our dummy minio
        def mock_upload_func(fileobj, dest_path, client=None):
            if client is None:
                client = mock_minio
            return client.put_object('voiceflow', dest_path, fileobj, 0)

        mock_upload.side_effect = mock_upload_func

        with TestClient(app) as test_client:
            yield test_client


class TestMultiTenantAgentSystem:
    """Test the complete multi-tenant agent system."""

    def test_tenant_creation(self, client):
        """Test tenant creation."""
        response = client.post('/tenants', json={'name': 'TestCompany'})
        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert data['name'] == 'TestCompany'

    def test_agent_creation(self, client):
        """Test agent creation within tenant."""
        # Create tenant first
        tenant_response = client.post('/tenants', json={'name': 'TestCompany'})
        tenant_id = tenant_response.json()['id']

        agent_response = client.post('/agents', json={
            'tenant_id': str(uuid.UUID(tenant_id)),  # Convert to UUID string
            'name': 'SupportBot',
            'description': 'Customer support agent'
        })
        assert agent_response.status_code == 200
        agent_data = agent_response.json()
        assert 'id' in agent_data
        assert agent_data['name'] == 'SupportBot'
        assert agent_data['tenant_id'] == tenant_id

    def test_agent_configuration(self, client):
        """Test agent configuration storage."""
        # Create tenant and agent
        tenant_response = client.post('/tenants', json={'name': 'TestCompany'})
        tenant_id = tenant_response.json()['id']

        agent_response = client.post('/agents', json={
            'tenant_id': str(uuid.UUID(tenant_id)),  # Convert to UUID string
            'name': 'SupportBot'
        })
        agent_id = agent_response.json()['agent_id']

        # Save agent configuration
        config_response = client.post('/agent-config',
            json={
                'agent_id': agent_id,
                'agent_name': 'SupportBot',
                'agent_role': 'Customer Support Specialist',
                'agent_description': 'Handles customer inquiries',        
                'personality_traits': ['helpful', 'patient'],
                'communication_channels': ['phone', 'chat'],
                'preferred_response_style': 'professional',
                'response_tone': 'friendly',
                'company_name': 'TestCompany',
                'industry': 'technology'
            }
        )
        assert config_response.status_code == 200        # Verify configuration was saved
        get_response = client.get(f'/agent-config/{agent_id}')
        assert get_response.status_code == 200
        config = get_response.json()
        assert config['agent_name'] == 'SupportBot'
        assert config['response_tone'] == 'friendly'

    def test_document_upload_and_ingestion(self, client, mock_minio):
        """Test document upload and ingestion process."""
        # Create tenant and agent
        tenant_response = client.post('/tenants', json={'name': 'TestCompany'})
        tenant_id = tenant_response.json()['id']

        agent_response = client.post('/agents', json={
            'tenant_id': tenant_id,
            'name': 'SupportBot'
        })
        agent_id = agent_response.json()['id']

        # Upload a document
        test_content = b"This is a test document for ingestion."
        files = {'file': ('test.txt', io.BytesIO(test_content), 'text/plain')}
        upload_response = client.post(f'/upload/{tenant_id}/{agent_id}', files=files)
        assert upload_response.status_code == 200

        upload_data = upload_response.json()
        assert 'id' in upload_data
        assert 'file_path' in upload_data
        document_id = upload_data['id']

        # Verify document was stored in MinIO
        assert upload_data['file_path'] in mock_minio.storage

        # Check documents list for agent
        docs_response = client.get(f'/documents/{agent_id}')
        assert docs_response.status_code == 200
        docs = docs_response.json().get('documents', [])
        assert len(docs) >= 1
        assert any(doc['id'] == document_id for doc in docs)

    def test_onboarding_flow(self, client):
        """Test the complete onboarding flow."""
        # Step 1: Company setup (using basic tenant creation)
        company_response = client.post('/tenants', json={
            'name': 'TestCompany'
        })
        assert company_response.status_code == 200
        tenant_id = company_response.json()['id']

        # Step 2: Agent creation (using basic agent creation)
        agent_response = client.post('/agents', json={
            'name': 'SupportBot',
            'tenant_id': tenant_id
        })
        assert agent_response.status_code == 200
        agent_data = agent_response.json()
        assert 'agent_id' in agent_data
        assert agent_data['name'] == 'SupportBot'

        # Step 4: Voice configuration
        voice_response = client.post('/onboarding/voice', json={
            'voice': 'sarah',
            'tone': 'professional',
            'language': 'en-US',
            'personality': 'helpful and patient'
        })
        assert voice_response.status_code == 200

        # Step 5: Agent config (combines agent details + voice)
        config_response = client.post('/onboarding/agent-config', json={
            'agent_name': 'SupportBot',
            'agent_role': 'Customer Support',
            'agent_description': 'Handles customer inquiries',
            'personality_traits': ['helpful'],
            'communication_channels': ['phone', 'chat'],
            'preferred_response_style': 'professional',
            'response_tone': 'friendly',
            'company_name': 'TestCompany'
        })
        assert config_response.status_code == 200

    def test_multi_tenant_isolation(self, client):
        """Test that tenants and agents are properly isolated."""
        # Create two tenants
        tenant1_response = client.post('/tenants', json={'name': 'CompanyA'})
        tenant1_id = tenant1_response.json()['id']

        tenant2_response = client.post('/tenants', json={'name': 'CompanyB'})
        tenant2_id = tenant2_response.json()['id']

        # Create agents for each tenant
        agent1_response = client.post('/agents', json={
            'tenant_id': str(uuid.UUID(tenant1_id)),  # Convert to UUID string
            'name': 'AgentA'
        })
        agent1_id = agent1_response.json()['agent_id']

        agent2_response = client.post('/agents', json={
            'tenant_id': str(uuid.UUID(tenant2_id)),  # Convert to UUID string
            'name': 'AgentB'
        })
        agent2_id = agent2_response.json()['agent_id']

        # Verify agents are isolated by tenant (check database directly since /agents requires auth)
        from backend.db import get_session
        from sqlalchemy import text
        import asyncio
        
        async def check_agents():
            async with get_session() as session:
                # Check tenant1 agents
                res1 = await session.execute(text('SELECT COUNT(*) FROM agents WHERE tenant_id = :tenant'), {'tenant': tenant1_id})
                count1 = res1.scalar()
                
                # Check tenant2 agents  
                res2 = await session.execute(text('SELECT COUNT(*) FROM agents WHERE tenant_id = :tenant'), {'tenant': tenant2_id})
                count2 = res2.scalar()
                
                return count1, count2
        
        count1, count2 = asyncio.run(check_agents())
        assert count1 == 1  # One agent for tenant1
        assert count2 == 1  # One agent for tenant2


class TestStandaloneDocumentIngestion:
    """Test standalone document ingestion without full agent setup."""

    def test_direct_document_ingestion(self, client, mock_minio):
        """Test direct document ingestion endpoint."""
        test_content = b"This is test content for standalone ingestion."
        files = {'file': ('standalone.txt', io.BytesIO(test_content), 'text/plain')}

        response = client.post('/ingest/document', files=files, data={'metadata': '{"source": "standalone_test"}'})
        assert response.status_code == 200

        data = response.json()
        assert data['success'] is True
        assert 'document_id' in data
        assert data['filename'] == 'standalone.txt'
        assert data['file_type'] == 'text'

    def test_website_scraping_standalone(self, client):
        """Test standalone website scraping."""
        # Mock the web scraper to avoid actual network calls
        with patch('services.web_scraper.WebScraper.scrape', return_value='Mocked website content'):
            response = client.post('/ingest/website', json={
                'url': 'https://example.com',
                'metadata': {'source': 'standalone_test'}
            })
            assert response.status_code == 200

            data = response.json()
            assert data['success'] is True
            assert 'document_id' in data
            assert data['url'] == 'https://example.com'

    def test_faq_ingestion_standalone(self, client):
        """Test standalone FAQ ingestion."""
        response = client.post('/ingest/faq', json={
            'content': 'Q: What is AI? A: Artificial Intelligence.',
            'metadata': {'source': 'standalone_test'}
        })
        assert response.status_code == 200

        data = response.json()
        assert data['success'] is True
        assert 'document_id' in data
        assert data['content_type'] == 'faq'

    def test_list_ingested_documents(self, client):
        """Test listing ingested documents."""
        response = client.get('/ingest/documents')
        assert response.status_code == 200

        data = response.json()
        assert 'documents' in data
        assert isinstance(data['documents'], list)

    def test_search_ingested_documents(self, client):
        """Test searching ingested documents."""
        # First ingest some content
        response = client.post('/ingest/faq', json={
            'content': 'Q: What is AI? A: Artificial Intelligence is a field of computer science.',
            'metadata': {'source': 'test_search'}
        })
        assert response.status_code == 200

        # Search for it
        response = client.post('/ingest/search', json={
            'query': 'artificial intelligence',
            'source': 'test_search'
        })
        assert response.status_code == 200

        data = response.json()
        assert 'results' in data
        assert isinstance(data['results'], list)


if __name__ == "__main__":
    pytest.main([__file__])
