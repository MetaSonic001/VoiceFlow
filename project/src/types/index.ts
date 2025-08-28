export interface User {
  id: string;
  email: string;
  name: string;
  company?: Company;
}

export interface Company {
  id: string;
  name: string;
  industry: string;
  domain: string;
  size: string;
  useCase: string;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'draft' | 'active' | 'paused';
  channels: Channel[];
  personality: AgentPersonality;
  voice: VoiceConfig;
  createdAt: string;
  totalCalls: number;
  successRate: number;
}

export interface Channel {
  type: 'phone' | 'chat' | 'whatsapp' | 'slack';
  enabled: boolean;
  config?: any;
}

export interface AgentPersonality {
  tone: 'formal' | 'friendly' | 'empathetic' | 'sales-driven';
  style: string;
  guidelines: string[];
}

export interface VoiceConfig {
  provider: string;
  voiceId: string;
  speed: number;
  stability: number;
}

export interface KnowledgeSource {
  id: string;
  type: 'document' | 'url' | 'integration';
  name: string;
  status: 'processing' | 'ready' | 'error';
  uploadedAt: string;
}

export interface CallAnalytics {
  totalCalls: number;
  successfulCalls: number;
  averageDuration: number;
  topIntents: string[];
  callVolume: { date: string; calls: number; }[];
}