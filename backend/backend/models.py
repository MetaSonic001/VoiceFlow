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


class Brand(Base):
    __tablename__ = 'brands'
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class Agent(Base):
    __tablename__ = 'agents'
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False)
    brand_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('brands.id'), nullable=True)
    name = sa.Column(sa.Text, nullable=False)
    status = sa.Column(sa.Text, nullable=True, default='active')
    description = sa.Column(sa.Text, nullable=True)
    channels = sa.Column(sa.JSON, nullable=True)
    phone_number = sa.Column(sa.Text, nullable=True)
    total_calls = sa.Column(sa.Integer, nullable=True, default=0)
    totalChats = sa.Column(sa.Integer, nullable=True, default=0)
    success_rate = sa.Column(sa.Integer, nullable=True, default=0)
    avg_response_time = sa.Column(sa.Text, nullable=True)
    chroma_collection = sa.Column(sa.Text, nullable=True)
    config_path = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)


class AgentConfiguration(Base):
    """Stores agent-specific configuration metadata from onboarding.
    
    This data is NOT part of the knowledge base but defines how the agent should behave,
    its personality, communication preferences, and business context. Used by agent workflow.
    """
    __tablename__ = 'agent_configurations'
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=False, unique=True)
    
    # Onboarding data - agent personality and behavior
    agent_name = sa.Column(sa.Text, nullable=True)
    agent_role = sa.Column(sa.Text, nullable=True)  # e.g., "Customer Support Agent", "Sales Assistant"
    agent_description = sa.Column(sa.Text, nullable=True)
    personality_traits = sa.Column(sa.JSON, nullable=True)  # e.g., ["friendly", "professional", "helpful"]
    
    # Communication preferences
    communication_channels = sa.Column(sa.JSON, nullable=True)  # ["chat", "email", "voice"]
    preferred_response_style = sa.Column(sa.Text, nullable=True)  # "formal", "casual", "technical"
    response_tone = sa.Column(sa.Text, nullable=True)  # "professional", "friendly", "empathetic"
    
    # Business context
    company_name = sa.Column(sa.Text, nullable=True)
    industry = sa.Column(sa.Text, nullable=True)
    primary_use_case = sa.Column(sa.Text, nullable=True)
    brief_description = sa.Column(sa.Text, nullable=True)
    
    # Agent behavior rules
    behavior_rules = sa.Column(sa.JSON, nullable=True)  # Custom rules for agent behavior
    escalation_triggers = sa.Column(sa.JSON, nullable=True)  # When to escalate to human
    knowledge_boundaries = sa.Column(sa.JSON, nullable=True)  # What the agent should/shouldn't handle
    
    # Workflow integration
    chroma_collection_name = sa.Column(sa.Text, nullable=True)  # Link to ChromaDB collection
    max_response_length = sa.Column(sa.Integer, nullable=True, default=500)
    confidence_threshold = sa.Column(sa.Float, nullable=True, default=0.7)  # For answer confidence
    
    # Metadata
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Document(Base):
    __tablename__ = 'documents'
    # Use Text primary key so this table can reference ingestion-managed string IDs
    id = sa.Column(sa.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=True)  # Allow NULL for standalone
    tenant_id = sa.Column(UUID(as_uuid=True), nullable=True)  # Allow NULL for standalone
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
    tenant_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=True)
    brand_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('brands.id'), nullable=True)
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


class OnboardingProgress(Base):
    __tablename__ = 'onboarding_progress'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_email = sa.Column(sa.Text, nullable=False, unique=True)
    tenant_id = sa.Column(UUID(as_uuid=True), nullable=True)
    agent_id = sa.Column(UUID(as_uuid=True), nullable=True)
    current_step = sa.Column(sa.Integer, nullable=True)
    data = sa.Column(sa.JSON, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
