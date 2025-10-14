from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, func
from .db import Base


class PipelineAgent(Base):
    __tablename__ = "pipeline_agents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    agent_type = Column(String, index=True)  # curator, evaluator, summarizer, qa
    tenant_id = Column(String, index=True, nullable=True)
    config = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())


class Pipeline(Base):
    __tablename__ = "pipelines"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    tenant_id = Column(String, index=True, nullable=True)
    stages = Column(JSON, default=list)  # list of {type, agent_id, settings}
    created_at = Column(DateTime, server_default=func.now())
