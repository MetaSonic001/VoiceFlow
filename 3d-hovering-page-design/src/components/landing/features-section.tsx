import { LANDING_FEATURES, LANDING_STATS } from '@/constants/features'

export function FeaturesSection() {
  return (
    <section id="features" className="py-16 md:py-24 bg-white border-t border-stone-200">
      <div className="max-w-7xl mx-auto px-8">
        <div className="text-center mb-16">
          <h2 className="font-serif text-4xl lg:text-5xl font-bold text-stone-900 mb-4">
            Everything you need to build AI voice agents
          </h2>
          <p className="font-serif text-stone-600 max-w-2xl mx-auto">
            From intelligent voice interactions to advanced analytics, VoiceFlow gives you the complete toolkit.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {LANDING_FEATURES.map((feature) => {
            const Icon = feature.icon
            return (
              <div
                key={feature.title}
                className="group p-6 rounded-2xl border border-stone-200 hover:border-stone-400 hover:shadow-lg transition-all bg-stone-50"
              >
                <div className="w-12 h-12 rounded-xl bg-stone-900 flex items-center justify-center text-stone-100 mb-4">
                  <Icon size={22} />
                </div>
                <h3 className="font-serif font-semibold text-lg text-stone-900 mb-2">
                  {feature.title}
                </h3>
                <p className="font-mono text-sm text-stone-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            )
          })}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-20">
          {LANDING_STATS.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="font-serif text-3xl font-bold text-stone-900">{stat.value}</div>
              <div className="font-mono text-sm text-stone-600 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
