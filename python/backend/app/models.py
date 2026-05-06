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
    campaigns = relationship("Campaign", back_populates="tenant", cascade="all, delete-orphan")
    webhook_endpoints = relationship("WebhookEndpoint", back_populates="tenant", cascade="all, delete-orphan")
    cloned_voices = relationship("ClonedVoice", back_populates="tenant", cascade="all, delete-orphan")
    kb_attachments = relationship("KbAttachment", back_populates="tenant", cascade="all, delete-orphan")
    voice_prints = relationship("VoicePrint", back_populates="tenant", cascade="all, delete-orphan")


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
    telephony_provider: Mapped[Optional[str]] = mapped_column(
        "telephonyProvider", String, nullable=True, default="twilio-gather"
    )
    # ── Prompt-to-Agent structured fields ────────────────────────────────────
    context_breakdown: Mapped[Optional[Any]] = mapped_column("contextBreakdown", JSON, nullable=True)
    # [{id, title, body, is_enabled, quality_score, auto_compliance}]
    welcome_message: Mapped[Optional[str]] = mapped_column("welcomeMessage", Text, nullable=True)
    post_call_actions: Mapped[Optional[Any]] = mapped_column("postCallActions", JSON, nullable=True)
    # [{variable, extraction_prompt, data_type}]
    integrations: Mapped[Optional[Any]] = mapped_column("integrations", JSON, nullable=True)
    # Per-agent integration config — overrides tenant.settings.integrations
    # {
    #   calcom:   {enabled, apiKey, eventTypeId, timezone},
    #   gcal:     {enabled, calendarId, credentialsJson},
    #   email:    {enabled, provider, host, port, username, password, recipients},
    #   hubspot:  {enabled, accessToken, fieldMap, createDeal, dealPipeline},
    #   salesforce: {enabled, instanceUrl, username, password, securityToken, objectType, fieldMap},
    #   slack:    {enabled, botToken, channel},
    #   webhooks: [{url, secret, enabled, label}],
    #   gohighlevel: {enabled, apiKey, locationId},
    # }
    language_config: Mapped[Optional[Any]] = mapped_column("languageConfig", JSON, nullable=True)
    # {primary_language, secondary_languages, geography, formality_level}
    caller_personas: Mapped[Optional[Any]] = mapped_column("callerPersonas", JSON, nullable=True)
    # [{name, intent, frustration_level, vocabulary_level}]
    simulation_suite: Mapped[Optional[Any]] = mapped_column("simulationSuite", JSON, nullable=True)
    # [{utterance, expected_intent, expected_keywords, must_not_contain, persona}]
    deployment_readiness_score: Mapped[Optional[int]] = mapped_column("deploymentReadinessScore", Integer, nullable=True)
    version_number: Mapped[int] = mapped_column("versionNumber", Integer, default=1)
    # ─────────────────────────────────────────────────────────────────────────
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="agents")
    brand = relationship("Brand", back_populates="agents")
    user = relationship("User", back_populates="agents")
    template = relationship("AgentTemplate", back_populates="agents")
    configuration = relationship("AgentConfiguration", back_populates="agent", uselist=False)
    documents = relationship("Document", back_populates="agent", cascade="all, delete-orphan")
    kb_attachments = relationship("KbAttachment", back_populates="agent", cascade="all, delete-orphan")
    call_logs = relationship("CallLog", back_populates="agent", cascade="all, delete-orphan")
    retraining_examples = relationship("RetrainingExample", back_populates="agent", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="agent", cascade="all, delete-orphan")
    versions = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan", order_by="AgentVersion.versionNumber.desc()")


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


# ── ClonedVoice ──────────────────────────────────────────────────────────────

class ClonedVoice(Base):
    """User-uploaded voice reference audio for voice cloning."""
    __tablename__ = "cloned_voices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    userId: Mapped[str] = mapped_column("userId", String, nullable=False, default="")
    name: Mapped[str] = mapped_column(String, nullable=False)
    languageCode: Mapped[str] = mapped_column("languageCode", String, nullable=False, default="en-IN")
    languageName: Mapped[Optional[str]] = mapped_column("languageName", String, nullable=True)
    # Storage key — format: "local:clones/…" or "minio:bucket/key"
    referenceAudioKey: Mapped[str] = mapped_column("referenceAudioKey", Text, nullable=False)
    durationSecs: Mapped[Optional[float]] = mapped_column("durationSecs", Float, nullable=True)
    # ready | error
    status: Mapped[str] = mapped_column(String, nullable=False, default="ready")
    errorMessage: Mapped[Optional[str]] = mapped_column("errorMessage", Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="cloned_voices")


# ── AgentVersion ──────────────────────────────────────────────────────────────

class AgentVersion(Base):
    """Immutable snapshot of an agent configuration at a point in time."""
    __tablename__ = "agent_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    tenantId: Mapped[str] = mapped_column("tenantId", String, nullable=False)
    versionNumber: Mapped[int] = mapped_column("versionNumber", Integer, default=1)
    changeDescription: Mapped[Optional[str]] = mapped_column("changeDescription", Text, nullable=True)
    snapshot: Mapped[Any] = mapped_column(JSON, nullable=False)
    # Full agent config at this version: {name, description, systemPrompt, voiceType,
    #   context_breakdown, welcome_message, post_call_actions, language_config,
    #   caller_personas, simulation_suite, ...}
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())

    agent = relationship("Agent", back_populates="versions")


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
    # File-type metadata for KB display
    fileType: Mapped[Optional[str]] = mapped_column("fileType", String, nullable=True)   # pdf/docx/txt/url/text
    chunkCount: Mapped[Optional[int]] = mapped_column("chunkCount", Integer, nullable=True)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="documents")
    agent = relationship("Agent", back_populates="documents")
    kb_attachments = relationship("KbAttachment", back_populates="document", cascade="all, delete-orphan")


# ── KbAttachment ─────────────────────────────────────────────────────────────

class KbAttachment(Base):
    """
    Attaches a Document to an Agent for Knowledge Base retrieval.
    Carries the when_to_use instruction that pre-filters retrieval at query time:
    if the user's query is not semantically relevant to when_to_use, this
    document's chunks are excluded — preventing irrelevant context from
    being injected into the LLM prompt.
    """
    __tablename__ = "kb_attachments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column(
        "tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    agentId: Mapped[str] = mapped_column(
        "agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    documentId: Mapped[str] = mapped_column(
        "documentId", String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    # Natural-language instruction: "Use this when the caller asks about pricing"
    whenToUse: Mapped[Optional[str]] = mapped_column("whenToUse", Text, nullable=True)
    chunkCount: Mapped[int] = mapped_column("chunkCount", Integer, default=0)
    # indexed | pending | error
    status: Mapped[str] = mapped_column(String, default="pending")
    errorMessage: Mapped[Optional[str]] = mapped_column("errorMessage", Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now()
    )
    updatedAt: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant = relationship("Tenant", back_populates="kb_attachments")
    agent = relationship("Agent", back_populates="kb_attachments")
    document = relationship("Document", back_populates="kb_attachments")


# ── VoicePrint ────────────────────────────────────────────────────────────────

class VoicePrint(Base):
    """
    Voice biometric voiceprint for speaker verification.
    Stores a 256-dim ECAPA-TDNN embedding per enrolled phone number.
    """
    __tablename__ = "voice_prints"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column(
        "tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    contactId: Mapped[Optional[str]] = mapped_column(
        "contactId", String, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    phoneNumber: Mapped[Optional[str]] = mapped_column("phoneNumber", String, nullable=True)
    # 256-dim float list (ECAPA-TDNN via resemblyzer)
    embedding: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # friendly name
    createdAt: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now()
    )

    tenant = relationship("Tenant", back_populates="voice_prints")


# ── CallLog ───────────────────────────────────────────────────────────────────

class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    callerPhone: Mapped[Optional[str]] = mapped_column("callerPhone", String, nullable=True)
    callSid: Mapped[Optional[str]] = mapped_column("callSid", String, nullable=True)           # Twilio/provider CallSid
    callDirection: Mapped[Optional[str]] = mapped_column("callDirection", String, nullable=True)  # inbound | outbound
    recordingUrl: Mapped[Optional[str]] = mapped_column("recordingUrl", String, nullable=True)  # recording link
    extractedVariables: Mapped[Optional[Any]] = mapped_column("extractedVariables", JSON, nullable=True)
    # Populated by extract_variables() post-call using agent.post_call_actions
    startedAt: Mapped[datetime] = mapped_column("startedAt", DateTime(timezone=True), nullable=False)
    endedAt: Mapped[Optional[datetime]] = mapped_column("endedAt", DateTime(timezone=True), nullable=True)
    durationSeconds: Mapped[Optional[int]] = mapped_column("durationSeconds", Integer, nullable=True)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    analysis: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ratingNotes: Mapped[Optional[str]] = mapped_column("ratingNotes", String, nullable=True)
    flaggedForRetraining: Mapped[bool] = mapped_column("flaggedForRetraining", Boolean, default=False)
    retrained: Mapped[bool] = mapped_column(Boolean, default=False)
    voicemailDetected: Mapped[bool] = mapped_column("voicemailDetected", Boolean, default=False)
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


# ── Campaign ──────────────────────────────────────────────────────────────────

class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # status: draft | active | paused | completed | failed
    status: Mapped[str] = mapped_column(String, default="draft", nullable=False)
    # Calling window e.g. {"start": "09:00", "end": "17:00"}
    allowedCallHours: Mapped[Optional[Any]] = mapped_column("allowedCallHours", JSON, nullable=True)
    timezone: Mapped[str] = mapped_column(String, default="UTC", nullable=False)
    maxRetries: Mapped[int] = mapped_column("maxRetries", Integer, default=3)
    # voicemail_action: leave_voicemail | hangup
    voicemailAction: Mapped[str] = mapped_column("voicemailAction", String, default="hangup")
    voicemailMessage: Mapped[Optional[str]] = mapped_column("voicemailMessage", Text, nullable=True)
    # Aggregate counters
    totalContacts: Mapped[int] = mapped_column("totalContacts", Integer, default=0)
    dialedCount: Mapped[int] = mapped_column("dialedCount", Integer, default=0)
    answeredCount: Mapped[int] = mapped_column("answeredCount", Integer, default=0)
    machinedCount: Mapped[int] = mapped_column("machinedCount", Integer, default=0)
    failedCount: Mapped[int] = mapped_column("failedCount", Integer, default=0)
    startedAt: Mapped[Optional[datetime]] = mapped_column("startedAt", DateTime(timezone=True), nullable=True)
    completedAt: Mapped[Optional[datetime]] = mapped_column("completedAt", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="campaigns")
    agent = relationship("Agent", back_populates="campaigns")
    contacts = relationship("CampaignContact", back_populates="campaign", cascade="all, delete-orphan")


# ── CampaignContact ───────────────────────────────────────────────────────────

class CampaignContact(Base):
    __tablename__ = "campaign_contacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    campaignId: Mapped[str] = mapped_column("campaignId", String, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    phoneNumber: Mapped[str] = mapped_column("phoneNumber", String, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    variables: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)  # extra CSV columns
    # status: pending | dialing | answered | voicemail | failed | skipped
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    callAttempts: Mapped[int] = mapped_column("callAttempts", Integer, default=0)
    lastCallSid: Mapped[Optional[str]] = mapped_column("lastCallSid", String, nullable=True)
    lastCalledAt: Mapped[Optional[datetime]] = mapped_column("lastCalledAt", DateTime(timezone=True), nullable=True)
    callLogId: Mapped[Optional[str]] = mapped_column("callLogId", String, ForeignKey("call_logs.id"), nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    campaign = relationship("Campaign", back_populates="contacts")
    tenant = relationship("Tenant")


# ── DNDRegistry ───────────────────────────────────────────────────────────────

class DNDRegistry(Base):
    """Do-Not-Disturb list. Numbers on this list are never dialled."""

    __tablename__ = "dnd_registry"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    phoneNumber: Mapped[str] = mapped_column("phoneNumber", String, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant")


# ── WebhookEndpoint ───────────────────────────────────────────────────────────

class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    # Comma-separated event types or JSON array stored as text
    events: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    secret: Mapped[str] = mapped_column(String, nullable=False, default=_uuid)
    isActive: Mapped[bool] = mapped_column("isActive", Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="webhook_endpoints")


# ── Contact (OmniCRM) ─────────────────────────────────────────────────────────

class Contact(Base):
    """
    Built-in CRM contact.  Accumulates call history for a phone number so that
    returning callers are greeted by name and given context automatically.
    Pre-call enrichment from HubSpot/Salesforce also lands here.
    """
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    phoneNumber: Mapped[str] = mapped_column("phoneNumber", String, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # intent_level: hot | warm | cold | not_interested
    intentLevel: Mapped[Optional[str]] = mapped_column("intentLevel", String, nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # positive | neutral | negative
    # CRM source IDs for bidirectional sync
    hubspotContactId: Mapped[Optional[str]] = mapped_column("hubspotContactId", String, nullable=True)
    salesforceLeadId: Mapped[Optional[str]] = mapped_column("salesforceLeadId", String, nullable=True)
    # Historical context pulled from CRM before the call
    crmContext: Mapped[Optional[Any]] = mapped_column("crmContext", JSON, nullable=True)
    # Extracted variables and custom facts from all past calls
    extractedData: Mapped[Optional[Any]] = mapped_column("extractedData", JSON, nullable=True)
    totalCalls: Mapped[int] = mapped_column("totalCalls", Integer, default=0)
    lastCalledAt: Mapped[Optional[datetime]] = mapped_column("lastCalledAt", DateTime(timezone=True), nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)  # list of string tags
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant")


# ── IVR Tree ──────────────────────────────────────────────────────────────────

class IVRTree(Base):
    """
    IVR routing layer that sits before the AI agent.
    Each node is either a menu (DTMF routing) or a leaf that routes to an agent.
    The full tree is stored as a JSON adjacency list in `nodes`.
    """
    __tablename__ = "ivr_trees"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # JSON tree: [{"id": "root", "message": "Press 1 for ...", "children": [
    #   {"id": "n1", "dtmf": "1", "agentId": "...", "label": "Sales"},
    #   {"id": "n2", "dtmf": "2", "agentId": "...", "label": "Support"}
    # ]}]
    nodes: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    isActive: Mapped[bool] = mapped_column("isActive", Boolean, default=True)
    phoneNumber: Mapped[Optional[str]] = mapped_column("phoneNumber", String, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())
    updatedAt: Mapped[datetime] = mapped_column("updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant")


# ── CallRecording ─────────────────────────────────────────────────────────────

class CallRecording(Base):
    """
    Audio recording stored in MinIO, linked to a CallLog.
    durationSeconds, waveformData, and timestampedTranscript enable
    a click-to-seek waveform player in the dashboard.
    """
    __tablename__ = "call_recordings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    callLogId: Mapped[str] = mapped_column("callLogId", String, ForeignKey("call_logs.id", ondelete="CASCADE"), nullable=False)
    # MinIO object key: recordings/{tenantId}/{callLogId}.wav
    minioKey: Mapped[str] = mapped_column("minioKey", String, nullable=False)
    durationSeconds: Mapped[Optional[int]] = mapped_column("durationSeconds", Integer, nullable=True)
    fileSizeBytes: Mapped[Optional[int]] = mapped_column("fileSizeBytes", Integer, nullable=True)
    # Consent disclosure included in opening? (required for recording)
    consentDisclosed: Mapped[bool] = mapped_column("consentDisclosed", Boolean, default=False)
    # Sparse waveform for UI: list of amplitude values (0.0–1.0) sampled at ~1s intervals
    waveformData: Mapped[Optional[Any]] = mapped_column("waveformData", JSON, nullable=True)
    # timestampedTranscript: [{"start_s": 4.5, "end_s": 6.2, "text": "...", "speaker": "agent"}]
    timestampedTranscript: Mapped[Optional[Any]] = mapped_column("timestampedTranscript", JSON, nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant")
    agent = relationship("Agent")


# ── CoachingCard ──────────────────────────────────────────────────────────────

class CoachingCard(Base):
    """
    AI-generated coaching suggestions from analyze_call().
    Tenant admin reviews and approves; approved cards are merged into
    the agent's systemPrompt automatically.
    status: pending | approved | rejected | applied
    """
    __tablename__ = "coaching_cards"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenantId: Mapped[str] = mapped_column("tenantId", String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    agentId: Mapped[str] = mapped_column("agentId", String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    callLogId: Mapped[Optional[str]] = mapped_column("callLogId", String, ForeignKey("call_logs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    # What the agent did wrong / could improve
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    # The specific prompt change — expressed as a diff-style instruction
    suggestedPromptDelta: Mapped[Optional[str]] = mapped_column("suggestedPromptDelta", Text, nullable=True)
    # Score improvement estimate (0.0–1.0)
    impactScore: Mapped[Optional[float]] = mapped_column("impactScore", Float, nullable=True)
    approvedBy: Mapped[Optional[str]] = mapped_column("approvedBy", String, nullable=True)
    approvedAt: Mapped[Optional[datetime]] = mapped_column("approvedAt", DateTime(timezone=True), nullable=True)
    appliedAt: Mapped[Optional[datetime]] = mapped_column("appliedAt", DateTime(timezone=True), nullable=True)
    createdAt: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant")
    agent = relationship("Agent")
