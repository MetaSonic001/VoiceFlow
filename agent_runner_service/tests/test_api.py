import pytest
from fastapi.testclient import TestClient
from agent_runner_service.main import app
from agent_runner_service import db as dbmod
from unittest.mock import patch


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    # Use a temporary sqlite DB for tests
    test_db = f"sqlite:///{tmp_path / 'test_agent_runner.db'}"
    monkeypatch.setenv('AGENT_RUNNER_DATABASE_URL', test_db)
    # Recreate tables
    from importlib import reload
    reload(dbmod)
    from agent_runner_service.db import Base, engine
    Base.metadata.create_all(bind=engine)


def test_create_agent_and_pipeline():
    client = TestClient(app)

    # Create a curator agent
    r = client.post('/agents', json={"name": "curator-1", "agent_type": "curator"})
    assert r.status_code == 200
    agent = r.json()
    assert agent['agent_type'] == 'curator'

    # Create a pipeline using this agent
    stages = [{"type": "curator", "agent_id": agent['id'], "settings": {"prompt": "extract"}}]
    r2 = client.post('/pipelines', json={"name": "pipeline-1", "tenant_id": "t1", "stages": stages})
    assert r2.status_code == 200
    pipeline = r2.json()
    assert pipeline['name'] == 'pipeline-1'


def test_trigger_pipeline_background(monkeypatch):
    client = TestClient(app)

    # Create agent & pipeline
    r = client.post('/agents', json={"name": "summ-1", "agent_type": "summarizer"})
    agent = r.json()
    stages = [{"type": "summarizer", "agent_id": agent['id'], "settings": {"prompt": "sum"}}]
    r2 = client.post('/pipelines', json={"name": "p2", "tenant_id": "t2", "stages": stages})
    pipeline = r2.json()

    # Mock Crew.kickoff via patching the crewai.Crew.kickoff method used in main.run_pipeline
    with patch('agent_runner_service.main.Crew.kickoff') as mk:
        mk.return_value = "ok-result"
        r3 = client.post(f"/pipelines/{pipeline['id']}/trigger")
        assert r3.status_code == 200
        assert r3.json().get('message') == 'Pipeline scheduled'
