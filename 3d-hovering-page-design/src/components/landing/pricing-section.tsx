import Link from 'next/link'
import { Check } from 'lucide-react'
import { PRICING_TIERS } from '@/constants/pricing'

export function PricingSection() {
  return (
    <section id="pricing" className="py-16 md:py-24 bg-stone-100 border-t border-stone-200">
      <div className="max-w-7xl mx-auto px-8">
        <div className="text-center mb-16">
          <h2 className="font-serif text-4xl lg:text-5xl font-bold text-stone-900 mb-4">
            Simple, transparent pricing
          </h2>
          <p className="font-mono text-stone-600">Start free, scale as you grow.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {PRICING_TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`rounded-2xl p-8 transition ${
                tier.highlighted
                  ? 'bg-stone-900 text-stone-100 shadow-xl relative'
                  : 'bg-white border border-stone-200 hover:shadow-lg'
              }`}
            >
              {tier.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-stone-100 text-stone-900 text-xs font-mono font-bold rounded-full">
                  POPULAR
                </div>
              )}

              <h3 className={`font-serif font-semibold text-lg mb-1 ${tier.highlighted ? 'text-stone-100' : 'text-stone-900'}`}>
                {tier.name}
              </h3>
              <div className={`font-serif text-3xl font-bold mb-4 ${tier.highlighted ? 'text-stone-100' : 'text-stone-900'}`}>
                {tier.price}
                {tier.period && (
                  <span className={`text-base font-normal ${tier.highlighted ? 'text-stone-400' : 'text-stone-500'}`}>
                    {tier.period}
                  </span>
                )}
              </div>
              <p className={`font-mono text-sm mb-6 ${tier.highlighted ? 'text-stone-400' : 'text-stone-600'}`}>
                {tier.description}
              </p>

              <ul className="space-y-3 text-sm mb-8">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2">
                    <Check size={16} className={tier.highlighted ? 'text-stone-300' : 'text-stone-700'} />
                    <span className={`font-mono ${tier.highlighted ? 'text-stone-300' : 'text-stone-700'}`}>
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              <Link
                href={tier.href}
                className={`block text-center py-3 rounded-lg font-serif font-semibold transition ${
                  tier.highlighted
                    ? 'bg-stone-100 text-stone-900 hover:bg-white'
                    : 'border border-stone-300 text-stone-900 hover:bg-stone-50'
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
