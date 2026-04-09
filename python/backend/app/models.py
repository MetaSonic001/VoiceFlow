"""
SQLAlchemy ORM models — exact mirror of prisma/schema.prisma.
Table names use the @@map() values from Prisma (e.g. "tenants", "agents").
"""
import uuid
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Tenant ────────────────────────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    apiKey: Mapped[str] = mapped_column("apiKey", String, unique=True, default=_uuid)
    settings: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    policyRules: Mapped[Optional[Any]] = mapped_column("policyRules", JSON, nullable=True)
    isActive: Mapped[bool] = mapped_column("isActive", Boolean, default=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    brands = relationship("Brand", back_populates="tenant", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    call_logs = relationship("CallLog", back_populates="tenant", cascade="all, delete-orphan")
    retraining_examples = relationship("RetrainingExample", back_populates="tenant", cascade="all, delete-orphan")
    onboarding_progress = relationship("OnboardingProgress", back_populates="tenant")
    pipelines = relationship("Pipeline", back_populates="tenant", cascade="all, delete-orphan")


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default="user")
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    brandId: Mapped[Optional[str]] = mapped_column("brandId", String, ForeignKey("brands.id"), nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="users")
    brand = relationship("Brand", back_populates="users")
    agents = relationship("Agent", back_populates="user")
    onboarding = relationship("OnboardingProgress", back_populates="user", uselist=False)


# ── Brand ─────────────────────────────────────────────────────────────────────

class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    brandVoice: Mapped[Optional[str]] = mapped_column("brandVoice", Text, nullable=True)
    allowedTopics: Mapped[Optional[Any]] = mapped_column("allowedTopics", JSON, nullable=True)
    restrictedTopics: Mapped[Optional[Any]] = mapped_column("restrictedTopics", JSON, nullable=True)
    policyRules: Mapped[Optional[Any]] = mapped_column("policyRules", JSON, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="brands")
    users = relationship("User", back_populates="brand")
    agents = relationship("Agent", back_populates="brand")


# ── Agent ─────────────────────────────────────────────────────────────────────

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    brandId: Mapped[Optional[str]] = mapped_column("brandId", String, ForeignKey("brands.id"), nullable=True)
    userId: Mapped[Optional[str]] = mapped_column("userId", String, ForeignKey("users.id"), nullable=True)
    templateId: Mapped[Optional[str]] = mapped_column("templateId", String, ForeignKey("agent_templates.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String, default="active")
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    systemPrompt: Mapped[Optional[str]] = mapped_column("systemPrompt", String, nullable=True)
    voiceType: Mapped[Optional[str]] = mapped_column("voiceType", String, default="female")
    channels: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    llmPreferences: Mapped[Optional[Any]] = mapped_column("llmPreferences", JSON, nullable=True)
    tokenLimit: Mapped[Optional[int]] = mapped_column("tokenLimit", Integer, default=4096)
    contextWindowStrategy: Mapped[Optional[str]] = mapped_column("contextWindowStrategy", String, default="condense")
    phoneNumber: Mapped[Optional[str]] = mapped_column("phoneNumber", String, nullable=True)
    twilioNumberSid: Mapped[Optional[str]] = mapped_column("twilioNumberSid", String, nullable=True)
    totalCalls: Mapped[Optional[int]] = mapped_column("totalCalls", Integer, default=0)
    totalChats: Mapped[Optional[int]] = mapped_column("totalChats", Integer, default=0)
    successRate: Mapped[Optional[int]] = mapped_column("successRate", Integer, default=0)
    avgResponseTime: Mapped[Optional[str]] = mapped_column("avgResponseTime", String, nullable=True)
    chromaCollection: Mapped[Optional[str]] = mapped_column("chromaCollection", String, nullable=True)
    configPath: Mapped[Optional[str]] = mapped_column("configPath", String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="agents")
    brand = relationship("Brand", back_populates="agents")
    user = relationship("User", back_populates="agents")
    template = relationship("AgentTemplate", back_populates="agents")
    configuration = relationship("AgentConfiguration", back_populates="agent", uselist=False)
    documents = relationship("Document", back_populates="agent", cascade="all, delete-orphan")
    call_logs = relationship("CallLog", back_populates="agent", cascade="all, delete-orphan")
    retraining_examples = relationship("RetrainingExample", back_populates="agent", cascade="all, delete-orphan")


# ── AgentConfiguration ────────────────────────────────────────────────────────

class AgentConfiguration(Base):
    __tablename__ = "agent_configurations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), unique=True, nullable=False)
    templateId: Mapped[Optional[str]] = mapped_column("templateId", String, ForeignKey("agent_templates.id"), nullable=True)
    agentName: Mapped[Optional[str]] = mapped_column("agentName", String, nullable=True)
    agentRole: Mapped[Optional[str]] = mapped_column("agentRole", String, nullable=True)
    agentDescription: Mapped[Optional[str]] = mapped_column("agentDescription", String, nullable=True)
    personalityTraits: Mapped[Optional[Any]] = mapped_column("personalityTraits", JSON, nullable=True)
    communicationChannels: Mapped[Optional[Any]] = mapped_column("communicationChannels", JSON, nullable=True)
    preferredResponseStyle: Mapped[Optional[str]] = mapped_column("preferredResponseStyle", String, nullable=True)
    responseTone: Mapped[Optional[str]] = mapped_column("responseTone", String, nullable=True)
    voiceId: Mapped[Optional[str]] = mapped_column("voiceId", String, nullable=True)
    voiceCloneSourceUrl: Mapped[Optional[str]] = mapped_column("voiceCloneSourceUrl", String, nullable=True)
    companyName: Mapped[Optional[str]] = mapped_column("companyName", String, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    primaryUseCase: Mapped[Optional[str]] = mapped_column("primaryUseCase", String, nullable=True)
    briefDescription: Mapped[Optional[str]] = mapped_column("briefDescription", String, nullable=True)
    behaviorRules: Mapped[Optional[Any]] = mapped_column("behaviorRules", JSON, nullable=True)
    escalationTriggers: Mapped[Optional[Any]] = mapped_column("escalationTriggers", JSON, nullable=True)
    knowledgeBoundaries: Mapped[Optional[Any]] = mapped_column("knowledgeBoundaries", JSON, nullable=True)
    chromaCollectionName: Mapped[Optional[str]] = mapped_column("chromaCollectionName", String, nullable=True)
    customInstructions: Mapped[Optional[str]] = mapped_column("customInstructions", Text, nullable=True)
    policyRules: Mapped[Optional[Any]] = mapped_column("policyRules", JSON, nullable=True)
    escalationRules: Mapped[Optional[Any]] = mapped_column("escalationRules", JSON, nullable=True)
    maxResponseLength: Mapped[Optional[int]] = mapped_column("maxResponseLength", Integer, default=500)
    confidenceThreshold: Mapped[Optional[float]] = mapped_column("confidenceThreshold", Float, default=0.7)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    agent = relationship("Agent", back_populates="configuration")
    template = relationship("AgentTemplate", back_populates="configurations")


# ── AgentTemplate ─────────────────────────────────────────────────────────────

class AgentTemplate(Base):
    __tablename__ = "agent_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    baseSystemPrompt: Mapped[str] = mapped_column("baseSystemPrompt", Text, nullable=False)
    defaultCapabilities: Mapped[Any] = mapped_column("defaultCapabilities", JSON, default=list)
    suggestedKnowledgeCategories: Mapped[Any] = mapped_column("suggestedKnowledgeCategories", JSON, default=list)
    defaultTools: Mapped[Any] = mapped_column("defaultTools", JSON, default=list)
    icon: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    isActive: Mapped[bool] = mapped_column("isActive", Boolean, default=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    agents = relationship("Agent", back_populates="template")
    configurations = relationship("AgentConfiguration", back_populates="template")


# ── OnboardingProgress ────────────────────────────────────────────────────────

class OnboardingProgress(Base):
    __tablename__ = "onboarding_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    userEmail: Mapped[str] = mapped_column("userEmail", String, ForeignKey("users.email"), unique=True, nullable=False)
    tenantId: Mapped[Optional[str]] = mapped_column("tenantId", String, ForeignKey("tenants.id"), nullable=True)
    agentId: Mapped[Optional[str]] = mapped_column("agentId", String, nullable=True)
    currentStep: Mapped[Optional[int]] = mapped_column("currentStep", Integer, nullable=True)
    data: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="onboarding")
    tenant = relationship("Tenant", back_populates="onboarding_progress")


# ── Document ──────────────────────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    s3Path: Mapped[Optional[str]] = mapped_column("s3Path", String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_: Mapped[Optional[Any]] = mapped_column("metadata", JSON, nullable=True)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="documents")
    agent = relationship("Agent", back_populates="documents")


# ── CallLog ───────────────────────────────────────────────────────────────────

class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    callerPhone: Mapped[Optional[str]] = mapped_column("callerPhone", String, nullable=True)
    startedAt: Mapped[datetime] = mapped_column("startedAt", DateTime(timezone=True), nullable=False)
    endedAt: Mapped[Optional[datetime]] = mapped_column("endedAt", DateTime(timezone=True), nullable=True)
    durationSeconds: Mapped[Optional[int]] = mapped_column("durationSeconds", Integer, nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    analysis: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ratingNotes: Mapped[Optional[str]] = mapped_column("ratingNotes", String, nullable=True)
    flaggedForRetraining: Mapped[bool] = mapped_column("flaggedForRetraining", Boolean, default=False)
    retrained: Mapped[bool] = mapped_column(Boolean, default=False)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant", back_populates="call_logs")
    agent = relationship("Agent", back_populates="call_logs")
    retraining_examples = relationship("RetrainingExample", back_populates="call_log", cascade="all, delete-orphan")


# ── RetrainingExample ─────────────────────────────────────────────────────────

class RetrainingExample(Base):
    __tablename__ = "retraining_examples"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    callLogId: Mapped[str] = mapped_column("callLogId", String, ForeignKey("call_logs.id", ondelete="CASCADE"), nullable=False)
    userQuery: Mapped[str] = mapped_column("userQuery", Text, nullable=False)
    badResponse: Mapped[str] = mapped_column("badResponse", Text, nullable=False)
    idealResponse: Mapped[str] = mapped_column("idealResponse", Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    approvedAt: Mapped[Optional[datetime]] = mapped_column("approvedAt", DateTime(timezone=True), nullable=True)
    approvedBy: Mapped[Optional[str]] = mapped_column("approvedBy", String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="retraining_examples")
    agent = relationship("Agent", back_populates="retraining_examples")
    call_log = relationship("CallLog", back_populates="retraining_examples")


# ── Pipeline ──────────────────────────────────────────────────────────────────

class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    stages: Mapped[Any] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="idle")
    lastRunAt: Mapped[Optional[datetime]] = mapped_column("lastRunAt", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="pipelines")


# ── AuditLog ──────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    userId: Mapped[Optional[str]] = mapped_column("userId", String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resourceId: Mapped[Optional[str]] = mapped_column("resourceId", String, nullable=True)
    details: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    ipAddress: Mapped[Optional[str]] = mapped_column("ipAddress", String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant")


# ── Notification ──────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    userId: Mapped[Optional[str]] = mapped_column("userId", String, nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)  # info, warning, success, error
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    isRead: Mapped[bool] = mapped_column("isRead", Boolean, default=False)
    link: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
