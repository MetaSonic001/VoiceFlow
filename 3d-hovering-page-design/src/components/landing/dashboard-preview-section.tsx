import Link from 'next/link'
import { Play, Volume2 } from 'lucide-react'

export function DashboardPreviewSection() {
  return (
    <section id="how-it-works" className="py-16 md:py-24 bg-stone-50 border-t border-stone-200">
      <div className="max-w-7xl mx-auto px-8">
        {/* Top Header */}
        <div className="mb-16">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-4 h-[1px] bg-stone-400" />
            <span className="font-mono text-xs uppercase tracking-widest text-stone-500">Getting Started Steps</span>
          </div>
          <h2 className="font-serif text-4xl lg:text-5xl font-bold text-stone-900 mb-4">
            Get up and running in no time
          </h2>
          <p className="font-serif text-stone-600 text-lg max-w-2xl">
            From sign-up to your first call in under 10 minutes.
          </p>
        </div>

        {/* Two Columns */}
        <div className="grid lg:grid-cols-12 gap-12 lg:gap-16 items-center">
          {/* Left Column - Steps */}
          <div className="lg:col-span-5 flex flex-col justify-between h-full">
            <div className="relative space-y-12 pl-6">
              {/* Dotted Vertical Connecting Line */}
              <div className="absolute left-[37px] top-[40px] bottom-[40px] w-[2px] border-l-2 border-dashed border-stone-300 z-0" />

              {/* Step 1 */}
              <div className="flex gap-6 relative z-10">
                <div className="w-10 h-10 rounded-full border border-stone-300 bg-white text-stone-800 flex items-center justify-center font-mono font-bold shrink-0 shadow-sm">
                  1
                </div>
                <div>
                  <h3 className="font-serif font-bold text-xl text-stone-900 mb-2">Create your agent</h3>
                  <p className="font-serif text-stone-600 leading-relaxed">
                    Use our intuitive builder interface to define agent details, prompt behaviors, and choose voices in minutes.
                  </p>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-6 relative z-10">
                <div className="w-10 h-10 rounded-full border border-stone-300 bg-white text-stone-800 flex items-center justify-center font-mono font-bold shrink-0 shadow-sm">
                  2
                </div>
                <div>
                  <h3 className="font-serif font-bold text-xl text-stone-900 mb-2">Connect your systems</h3>
                  <p className="font-serif text-stone-600 leading-relaxed">
                    Link with webhooks, phone numbers, and customize API interactions to integrate workflows seamlessly.
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-6 relative z-10">
                <div className="w-10 h-10 rounded-full border border-stone-300 bg-white text-stone-800 flex items-center justify-center font-mono font-bold shrink-0 shadow-sm">
                  3
                </div>
                <div>
                  <h3 className="font-serif font-bold text-xl text-stone-900 mb-2">Deploy & scale</h3>
                  <p className="font-serif text-stone-600 leading-relaxed">
                    Publish your agent live. Monitor performance real-time and handle concurrent calls with top success rates.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-12 pl-16">
              <Link href="/register">
                <button className="bg-stone-900 text-white px-8 py-4 rounded-xl font-serif text-lg hover:bg-stone-800 transition-colors shadow-sm cursor-pointer">
                  Sign up for free
                </button>
              </Link>
            </div>
          </div>

          {/* Right Column - Premium Dashboard Mockup */}
          <div className="lg:col-span-7">
            {/* Video-player style frame with matching aesthetic stone bezel */}
            <div className="bg-gradient-to-tr from-stone-900 via-stone-800 to-stone-900 p-1.5 rounded-3xl border border-stone-300/60 shadow-2xl relative group overflow-hidden">
              {/* Inner content (the dashboard itself) */}
              <div className="bg-stone-950 rounded-[1.2rem] overflow-hidden border border-stone-800/40">
                
                {/* Browser/Window Header */}
                <div className="bg-stone-900 px-4 py-3 flex items-center gap-2 border-b border-stone-800 select-none">
                  {/* MacOS buttons */}
                  <div className="flex gap-1.5 mr-2">
                    <span className="w-3 h-3 rounded-full bg-[#ff5f56]" />
                    <span className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
                    <span className="w-3 h-3 rounded-full bg-[#27c93f]" />
                  </div>
                  {/* Address bar mock */}
                  <div className="flex-1 max-w-sm mx-auto bg-stone-950 rounded-lg py-1 px-3 text-center text-xs font-mono text-stone-500 flex items-center justify-center gap-1.5">
                    <span className="w-3 h-3 text-stone-600">🔒</span> voiceflow.ai/dashboard
                  </div>
                </div>

                {/* Dashboard Inner App Shell */}
                <div className="flex aspect-[16/10] text-stone-200 text-left select-none overflow-hidden text-[9px] sm:text-[10px] md:text-xs">
                  {/* Mock Sidebar */}
                  <aside className="w-1/4 bg-stone-900 border-r border-stone-800 p-3 flex flex-col justify-between shrink-0 font-sans">
                    <div className="space-y-4">
                      {/* Logo */}
                      <div className="flex items-center gap-2 px-1">
                        <div className="w-5 h-5 bg-stone-100 rounded-md flex items-center justify-center">
                          <span className="text-stone-955 font-serif font-bold text-[10px]">V</span>
                        </div>
                        <span className="font-serif font-bold text-stone-100 text-sm hidden sm:inline">VoiceFlow</span>
                      </div>
                      
                      {/* Sidebar sections */}
                      <div className="space-y-3 pt-2">
                        <div>
                          <div className="text-[8px] font-mono uppercase text-stone-500 tracking-wider mb-1.5 px-1">Core</div>
                          <ul className="space-y-1">
                            <li className="bg-stone-800 text-stone-100 font-semibold px-2 py-1 rounded flex items-center gap-2">
                              <span className="w-3 h-3 rounded-full bg-stone-100 flex items-center justify-center text-stone-950 text-[6px]">🏠</span>
                              <span className="hidden sm:inline">Dashboard</span>
                            </li>
                            <li className="text-stone-400 hover:text-stone-200 px-2 py-1 rounded flex items-center gap-2">
                              <span>⚡</span>
                              <span className="hidden sm:inline">Voice Agent</span>
                            </li>
                            <li className="text-stone-400 hover:text-stone-200 px-2 py-1 rounded flex items-center gap-2">
                              <span>📖</span>
                              <span className="hidden sm:inline">Voice Library</span>
                            </li>
                          </ul>
                        </div>
                        
                        <div>
                          <div className="text-[8px] font-mono uppercase text-stone-500 tracking-wider mb-1.5 px-1">Intelligence</div>
                          <ul className="space-y-1">
                            <li className="text-stone-400 hover:text-stone-200 px-2 py-1 rounded flex items-center gap-2">
                              <span>📊</span>
                              <span className="hidden sm:inline">Analytics</span>
                            </li>
                            <li className="text-stone-400 hover:text-stone-200 px-2 py-1 rounded flex items-center gap-2">
                              <span>📋</span>
                              <span className="hidden sm:inline">Reports</span>
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-stone-800 text-[8px] text-stone-500 font-mono">
                      v1.0.0
                    </div>
                  </aside>

                  {/* Mock Main Dashboard View */}
                  <main className="flex-1 bg-stone-950 p-4 overflow-y-auto space-y-4 font-sans">
                    {/* Header */}
                    <div className="flex items-center justify-between pb-2 border-b border-stone-900">
                      <div>
                        <h4 className="text-sm font-serif font-bold text-stone-100">AI Agents Dashboard</h4>
                        <p className="text-[9px] text-stone-500 font-mono">Manage and monitor your voice AI agents</p>
                      </div>
                      <div className="bg-stone-900 border border-stone-800 rounded-lg px-2.5 py-1 text-stone-300 font-serif font-semibold text-[10px] hover:bg-stone-800 cursor-pointer">
                        + Create Agent
                      </div>
                    </div>

                    {/* KPI Cards Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      <div className="bg-stone-900/60 border border-stone-800/80 rounded-xl p-2.5 flex flex-col justify-between">
                        <span className="text-[8px] uppercase tracking-wider text-stone-500 font-mono">Active Agents</span>
                        <div className="flex items-baseline gap-1 mt-1">
                          <span className="text-sm font-bold text-stone-100">3</span>
                          <span className="text-[8px] text-emerald-500">● Live</span>
                        </div>
                      </div>
                      <div className="bg-stone-900/60 border border-stone-800/80 rounded-xl p-2.5 flex flex-col justify-between">
                        <span className="text-[8px] uppercase tracking-wider text-stone-500 font-mono">Total Calls</span>
                        <div className="flex items-baseline gap-1 mt-1">
                          <span className="text-sm font-bold text-stone-100">1,482</span>
                        </div>
                      </div>
                      <div className="bg-stone-900/60 border border-stone-800/80 rounded-xl p-2.5 flex flex-col justify-between">
                        <span className="text-[8px] uppercase tracking-wider text-stone-500 font-mono">Avg Success</span>
                        <div className="flex items-baseline gap-1 mt-1">
                          <span className="text-sm font-bold text-stone-100">98.4</span>
                          <span className="text-[8px] text-stone-400">%</span>
                        </div>
                      </div>
                      <div className="bg-stone-900/60 border border-stone-800/80 rounded-xl p-2.5 flex flex-col justify-between">
                        <span className="text-[8px] uppercase tracking-wider text-stone-500 font-mono">Total Configured</span>
                        <div className="flex items-baseline gap-1 mt-1">
                          <span className="text-sm font-bold text-stone-100">5</span>
                          <span className="text-[8px] text-stone-400">Agents</span>
                        </div>
                      </div>
                    </div>

                    {/* Agent Cards Section */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h5 className="text-xs font-serif font-bold text-stone-300">Your Configured Agents</h5>
                        <span className="text-[8px] text-stone-500 font-mono">3 Active • 2 Inactive</span>
                      </div>

                      {/* Configured Agent list */}
                      <div className="grid md:grid-cols-2 gap-2">
                        {/* Card 1 */}
                        <div className="bg-stone-900 border border-stone-800/80 hover:border-stone-700/80 rounded-xl p-3 flex flex-col justify-between transition-colors">
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-serif font-semibold text-stone-200">Customer Support</span>
                              <span className="bg-emerald-950 text-emerald-400 border border-emerald-900 rounded-full px-1.5 py-0.5 text-[8px] font-mono font-medium scale-90">Active</span>
                            </div>
                            <p className="text-stone-400 text-[9px] line-clamp-1">Support bot handling inquiries and payments.</p>
                          </div>
                          <div className="flex justify-between items-center mt-3 pt-2 border-t border-stone-800/60 text-stone-500 text-[8px] font-mono">
                            <span>820 calls today</span>
                            <span className="text-stone-300 font-bold">97% accuracy</span>
                          </div>
                        </div>

                        {/* Card 2 */}
                        <div className="bg-stone-900 border border-stone-800/80 hover:border-stone-700/80 rounded-xl p-3 flex flex-col justify-between transition-colors">
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-serif font-semibold text-stone-200">Sales Representative</span>
                              <span className="bg-emerald-950 text-emerald-400 border border-emerald-900 rounded-full px-1.5 py-0.5 text-[8px] font-mono font-medium scale-90">Active</span>
                            </div>
                            <p className="text-stone-400 text-[9px] line-clamp-1">Outbound representative doing warm followups.</p>
                          </div>
                          <div className="flex justify-between items-center mt-3 pt-2 border-t border-stone-800/60 text-stone-500 text-[8px] font-mono">
                            <span>482 calls today</span>
                            <span className="text-stone-300 font-bold">98% accuracy</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </main>
                </div>

                {/* Bottom Controls Bar (Video player effect) */}
                <div className="bg-stone-900/90 px-4 py-3 flex items-center justify-between border-t border-stone-800 text-stone-400 text-xs font-mono">
                  <div className="flex items-center gap-4">
                    <button className="text-stone-200 hover:text-white transition-colors cursor-pointer">
                      <Play size={14} fill="currentColor" />
                    </button>
                    <div className="w-32 bg-stone-800 h-1 rounded-full relative overflow-hidden hidden sm:block">
                      <div className="absolute left-0 top-0 bottom-0 w-1/3 bg-stone-300" />
                    </div>
                    <span className="text-[10px] text-stone-500">03:14 / 09:40</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Volume2 size={14} className="text-stone-300" />
                    <span className="text-[10px] text-stone-500">100%</span>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>

      </div>
    </section>
  )
}
