export function LandingFooter() {
  return (
    <footer id="contact" className="bg-stone-900 text-stone-400 py-12 border-t border-stone-800">
      <div className="max-w-7xl mx-auto px-8 text-center">
        <div className="flex items-center justify-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-stone-100 flex items-center justify-center">
            <span className="font-serif font-bold text-stone-900 text-sm">V</span>
          </div>
          <span className="text-stone-100 font-serif font-bold">VoiceFlow AI</span>
        </div>
        <p className="font-mono text-sm mb-2">hello@voiceflow.ai</p>
        <p className="font-mono text-sm">&copy; 2026 VoiceFlow AI Platform. All rights reserved.</p>
      </div>
    </footer>
  )
}
