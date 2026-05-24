import {
  BarChart3,
  Headphones,
  MessageSquare,
  Mic,
  RefreshCw,
  Shield,
  Sliders,
  PhoneForwarded,
  type LucideIcon,
} from 'lucide-react'

export interface LandingFeature {
  title: string
  description: string
  icon: LucideIcon
}

export const LANDING_FEATURES: LandingFeature[] = [
  {
    title: 'Human-like Voice AI',
    description: 'Natural-sounding voices with local voice cloning for brand-consistent conversations.',
    icon: Mic,
  },
  {
    title: 'Intelligent Understanding',
    description: 'RAG-powered knowledge retrieval with hierarchical context for accurate answers.',
    icon: Headphones,
  },
  {
    title: 'Multi-channel Support',
    description: 'Deploy across phone, website chat, WhatsApp, and embeddable widgets.',
    icon: MessageSquare,
  },
  {
    title: 'Enterprise Security',
    description: 'Per-tenant encrypted credentials and isolated vector stores.',
    icon: Shield,
  },
  {
    title: 'Advanced Analytics',
    description: 'Real-time dashboards, call logs with transcripts, and performance tracking.',
    icon: BarChart3,
  },
  {
    title: 'Easy Customization',
    description: 'Agent templates, configurable personas, tone, language, and brand voice.',
    icon: Sliders,
  },
  {
    title: 'Continuous Improvement',
    description: 'Flag bad responses, review retraining queue, and trigger knowledge updates.',
    icon: RefreshCw,
  },
  {
    title: 'Smart Call Routing',
    description: 'Automatic escalation to human agents with full context transfer.',
    icon: PhoneForwarded,
  },
]

export const LANDING_STATS = [
  { value: '0.3s', label: 'Response Time' },
  { value: '10M+', label: 'Conversations' },
  { value: '96.8%', label: 'Satisfaction' },
  { value: '80%', label: 'Cost Reduction' },
] as const
