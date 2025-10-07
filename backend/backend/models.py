import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from .db import Base
import uuid
from datetime import datetime
import enum


class Tenant(Base):
    __tablename__ = 'tenants'
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class Agent(Base):
    __tablename__ = 'agents'
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    chroma_collection = sa.Column(sa.Text, nullable=True)
    config_path = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = 'documents'
    # Use Text primary key so this table can reference ingestion-managed string IDs
    id = sa.Column(sa.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=False)
    tenant_id = sa.Column(UUID(as_uuid=True), nullable=False)
    filename = sa.Column(sa.Text, nullable=False)
    file_path = sa.Column(sa.Text, nullable=False)
    file_type = sa.Column(sa.Text, nullable=True)
    # Store raw content and metadata so this table can act as the canonical ingestion store
    content = sa.Column(sa.LargeBinary, nullable=True)
    # 'metadata' is a reserved attribute name on Declarative classes; use
    # a different attribute name but keep the DB column name as 'metadata'.
    doc_metadata = sa.Column('metadata', sa.JSON, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = sa.Column(sa.Text, nullable=True)
    error_message = sa.Column(sa.Text, nullable=True)
    uploaded_by = sa.Column(UUID(as_uuid=True), nullable=True)
    uploaded_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    embedding_status = sa.Column(sa.Text, default='pending')


class UserRole(enum.Enum):
    admin = 'admin'
    user = 'user'
    guest = 'guest'


class User(Base):
    __tablename__ = 'users'
    id = sa.Column(sa.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = sa.Column(sa.Text, unique=True, nullable=False)
    password_hash = sa.Column(sa.Text, nullable=True)
    role = sa.Column(sa.Enum(UserRole), default=UserRole.user)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class PipelineAgent(Base):
    """Represents a specialized agent that can be used as a step in pipelines.

    Examples: knowledge_curator, evaluator, summarizer, qa_auditor
    """
    __tablename__ = 'pipeline_agents'
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = sa.Column(UUID(as_uuid=True), nullable=False)
    agent_id = sa.Column(UUID(as_uuid=True), nullable=True)
    name = sa.Column(sa.Text, nullable=False)
    agent_type = sa.Column(sa.Text, nullable=False)  # e.g. 'curator', 'evaluator', 'summarizer', 'qa'
    config = sa.Column(sa.JSON, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class Pipeline(Base):
    """Defines a pipeline (ordered steps) that can be executed for an agent/tenant.

    The `stages` JSON column is expected to be a list of objects like:
      [{"type": "curator", "agent_ref": "<pipeline_agent_id>", "settings": {...}}, ...]
    """
    __tablename__ = 'pipelines'
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = sa.Column(UUID(as_uuid=True), nullable=False)
    agent_id = sa.Column(UUID(as_uuid=True), nullable=True)
    name = sa.Column(sa.Text, nullable=False)
    stages = sa.Column(sa.JSON, nullable=False, default=list)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
