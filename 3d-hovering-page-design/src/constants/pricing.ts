export interface PricingTier {
  name: string
  price: string
  period?: string
  description: string
  features: string[]
  cta: string
  href: string
  highlighted?: boolean
}

export const PRICING_TIERS: PricingTier[] = [
  {
    name: 'Starter',
    price: '$99',
    period: '/mo',
    description: 'For teams getting started with voice AI.',
    features: [
      '2 AI Agents',
      '1,000 conversations/mo',
      'Phone + Chat',
      'Basic analytics',
    ],
    cta: 'Get Started',
    href: '/register',
  },
  {
    name: 'Professional',
    price: '$299',
    period: '/mo',
    description: 'For growing teams that need scale and depth.',
    features: [
      '10 AI Agents',
      '10,000 conversations/mo',
      'All channels + voice cloning',
      'Advanced analytics & retraining',
    ],
    cta: 'Get Started',
    href: '/register',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    description: 'For organizations with advanced security needs.',
    features: [
      'Unlimited agents',
      'Unlimited conversations',
      'SSO + custom integrations',
      'Dedicated support',
    ],
    cta: 'Contact Sales',
    href: '#contact',
  },
]
