-- VoiceFlow schema — created from prisma/schema.prisma
-- This creates all 11 tables matching the Prisma schema exactly.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tenants
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name TEXT NOT NULL,
    domain TEXT UNIQUE,
    "apiKey" TEXT UNIQUE DEFAULT uuid_generate_v4()::text,
    settings JSONB,
    "policyRules" JSONB,
    "isActive" BOOLEAN DEFAULT true,
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Brands
CREATE TABLE IF NOT EXISTS brands (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    "tenantId" TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    "brandVoice" TEXT,
    "allowedTopics" JSONB,
    "restrictedTopics" JSONB,
    "policyRules" JSONB,
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    role TEXT DEFAULT 'user',
    "tenantId" TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    "brandId" TEXT REFERENCES brands(id),
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Agent Templates
CREATE TABLE IF NOT EXISTS agent_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    "baseSystemPrompt" TEXT NOT NULL,
    "defaultCapabilities" JSONB DEFAULT '[]'::jsonb,
    "suggestedKnowledgeCategories" JSONB DEFAULT '[]'::jsonb,
    "defaultTools" JSONB DEFAULT '[]'::jsonb,
    icon TEXT,
    "isActive" BOOLEAN DEFAULT true,
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Agents
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    "tenantId" TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    "brandId" TEXT REFERENCES brands(id),
    "userId" TEXT REFERENCES users(id),
    "templateId" TEXT REFERENCES agent_templates(id),
    name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    description TEXT,
    "systemPrompt" TEXT,
    "voiceType" TEXT DEFAULT 'female',
    channels JSONB,
    "llmPreferences" JSONB,
    "tokenLimit" INTEGER DEFAULT 4096,
    "contextWindowStrategy" TEXT DEFAULT 'condense',
    "phoneNumber" TEXT,
    "twilioNumberSid" TEXT,
    "totalCalls" INTEGER DEFAULT 0,
    "totalChats" INTEGER DEFAULT 0,
    "successRate" INTEGER DEFAULT 0,
    "avgResponseTime" TEXT,
    "chromaCollection" TEXT,
    "configPath" TEXT,
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Agent Configurations
CREATE TABLE IF NOT EXISTS agent_configurations (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    "agentId" TEXT UNIQUE NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    "templateId" TEXT REFERENCES agent_templates(id),
    "agentName" TEXT,
    "agentRole" TEXT,
    "agentDescription" TEXT,
    "personalityTraits" JSONB,
    "communicationChannels" JSONB,
    "preferredResponseStyle" TEXT,
    "responseTone" TEXT,
    "voiceId" TEXT,
    "voiceCloneSourceUrl" TEXT,
    "companyName" TEXT,
    industry TEXT,
    "primaryUseCase" TEXT,
    "briefDescription" TEXT,
    "behaviorRules" JSONB,
    "escalationTriggers" JSONB,
    "knowledgeBoundaries" JSONB,
    "chromaCollectionName" TEXT,
    "customInstructions" TEXT,
    "policyRules" JSONB,
    "escalationRules" JSONB,
    "maxResponseLength" INTEGER DEFAULT 500,
    "confidenceThreshold" DOUBLE PRECISION DEFAULT 0.7,
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Onboarding Progress
CREATE TABLE IF NOT EXISTS onboarding_progress (
    id SERIAL PRIMARY KEY,
    "userEmail" TEXT UNIQUE NOT NULL REFERENCES users(email),
    "tenantId" TEXT REFERENCES tenants(id),
    "agentId" TEXT,
    "currentStep" INTEGER,
    data JSONB,
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    url TEXT,
    "s3Path" TEXT,
    status TEXT DEFAULT 'pending',
    title TEXT,
    content TEXT,
    metadata JSONB,
    "tenantId" TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    "agentId" TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Call Logs
CREATE TABLE IF NOT EXISTS call_logs (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    "tenantId" TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    "agentId" TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    "callerPhone" TEXT,
    "startedAt" TIMESTAMPTZ NOT NULL,
    "endedAt" TIMESTAMPTZ,
    "durationSeconds" INTEGER,
    transcript TEXT NOT NULL,
    analysis JSONB,
    rating INTEGER,
    "ratingNotes" TEXT,
    "flaggedForRetraining" BOOLEAN DEFAULT false,
    retrained BOOLEAN DEFAULT false,
    "createdAt" TIMESTAMPTZ DEFAULT now()
);

-- Retraining Examples
CREATE TABLE IF NOT EXISTS retraining_examples (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    "tenantId" TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    "agentId" TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    "callLogId" TEXT NOT NULL REFERENCES call_logs(id) ON DELETE CASCADE,
    "userQuery" TEXT NOT NULL,
    "badResponse" TEXT NOT NULL,
    "idealResponse" TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    "approvedAt" TIMESTAMPTZ,
    "approvedBy" TEXT,
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Pipelines
CREATE TABLE IF NOT EXISTS pipelines (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    "tenantId" TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    stages JSONB DEFAULT '[]'::jsonb,
    status TEXT DEFAULT 'idle',
    "lastRunAt" TIMESTAMPTZ,
    "createdAt" TIMESTAMPTZ DEFAULT now(),
    "updatedAt" TIMESTAMPTZ DEFAULT now()
);

-- Prisma migrations table (so Prisma doesn't complain later)
CREATE TABLE IF NOT EXISTS _prisma_migrations (
    id TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    finished_at TIMESTAMPTZ,
    migration_name TEXT NOT NULL,
    logs TEXT,
    rolled_back_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ DEFAULT now(),
    applied_steps_count INTEGER DEFAULT 0
);
