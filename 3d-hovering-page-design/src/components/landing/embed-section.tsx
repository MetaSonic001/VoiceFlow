export function EmbedSection() {
  return (
    <section id="embed" className="py-16 md:py-24 bg-stone-900 text-stone-100 border-t border-stone-800">
      <div className="max-w-7xl mx-auto px-8">
        <div className="text-center mb-16">
          <h2 className="font-serif text-4xl lg:text-5xl font-bold mb-4">
            Add AI voice to your website in one line
          </h2>
          <p className="font-serif text-stone-400 max-w-2xl mx-auto">
            Embed a powerful AI agent on any website with a simple script tag. Works everywhere — WordPress, Shopify, React, or plain HTML.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <div className="bg-stone-800 rounded-xl p-6 border border-stone-700 font-mono text-sm">
              <div className="flex items-center gap-2 mb-3 text-stone-500 text-xs">
                <span className="w-3 h-3 rounded-full bg-red-500" />
                <span className="w-3 h-3 rounded-full bg-yellow-500" />
                <span className="w-3 h-3 rounded-full bg-green-500" />
                index.html
              </div>
              <code className="text-green-400 break-all">
                {'<script src="https://your-domain.com/widget/embed.js"></script>'}
              </code>
            </div>
            <div className="flex flex-wrap gap-6 mt-8 text-sm font-mono text-stone-400">
              <span>Works everywhere</span>
              <span>Voice & text</span>
              <span>REST API</span>
            </div>
          </div>

          <div className="bg-stone-800 rounded-2xl p-4 border border-stone-700">
            <div className="bg-stone-100 rounded-xl p-4 text-stone-900">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-full bg-stone-900 flex items-center justify-center text-stone-100 text-xs font-serif font-bold">
                  AI
                </div>
                <span className="font-serif font-semibold text-sm">AI Assistant</span>
                <span className="ml-auto text-xs font-mono text-green-700">Online</span>
              </div>
              <div className="space-y-2 text-sm font-mono">
                <div className="bg-stone-200 rounded-lg px-3 py-2 max-w-[80%]">Hello! How can I help you today?</div>
                <div className="bg-stone-900 text-stone-100 rounded-lg px-3 py-2 max-w-[80%] ml-auto">What plans do you offer?</div>
                <div className="bg-stone-200 rounded-lg px-3 py-2 max-w-[80%]">We have Starter, Pro, and Enterprise plans. Would you like details?</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
