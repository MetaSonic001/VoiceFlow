import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Code, Copy, Check, Globe, MessageSquare, Zap, ArrowRight } from 'lucide-react';
import { Button } from './ui/button';

interface EmbedWidgetProps {
  onGetStarted: () => void;
}

export const EmbedWidget: React.FC<EmbedWidgetProps> = ({ onGetStarted }) => {
  const [copied, setCopied] = useState(false);

  const embedCode = `<script src="https://app.voiceflow.ai/api/widget/YOUR_AGENT_ID/embed.js"></script>`;

  const handleCopy = () => {
    navigator.clipboard.writeText(embedCode).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="py-20 bg-gradient-to-br from-gray-900 via-gray-800 to-slate-900 relative overflow-hidden">
      {/* Subtle grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:32px_32px]" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left — copy */}
          <motion.div
            className="space-y-6"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 text-sm font-medium border border-blue-500/30">
              <Code className="h-3.5 w-3.5 mr-2" />
              One-Line Integration
            </div>

            <h2 className="text-3xl lg:text-4xl font-bold text-white leading-tight">
              Add an AI agent to any website<br />
              <span className="text-blue-400">in one line of HTML</span>
            </h2>

            <p className="text-lg text-gray-300 leading-relaxed">
              Paste a single <code className="px-1.5 py-0.5 rounded bg-gray-700 text-blue-300 text-sm font-mono">&lt;script&gt;</code> tag 
              into your site and give every visitor access to a voice AI agent trained on your company's 
              knowledge base. No iframes, no SDKs, no backend changes.
            </p>

            <div className="grid sm:grid-cols-3 gap-4 pt-2">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                  <Globe className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <p className="text-white font-medium text-sm">Works everywhere</p>
                  <p className="text-gray-400 text-xs">WordPress, Shopify, React, plain HTML</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
                  <MessageSquare className="w-4 h-4 text-green-400" />
                </div>
                <div>
                  <p className="text-white font-medium text-sm">Voice & text</p>
                  <p className="text-gray-400 text-xs">Push-to-talk mic + chat input</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                  <Zap className="w-4 h-4 text-purple-400" />
                </div>
                <div>
                  <p className="text-white font-medium text-sm">REST API too</p>
                  <p className="text-gray-400 text-xs">Full API for custom integrations</p>
                </div>
              </div>
            </div>

            <Button 
              size="lg" 
              onClick={onGetStarted}
              className="group bg-blue-600 hover:bg-blue-700"
            >
              Create Your Widget
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Button>
          </motion.div>

          {/* Right — code block + mock widget */}
          <motion.div
            className="space-y-4"
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            {/* Code snippet */}
            <div className="rounded-xl border border-gray-700 bg-gray-950 shadow-2xl overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 bg-gray-800/80 border-b border-gray-700">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80" />
                  <span className="ml-3 text-xs text-gray-400 font-mono">your-website.html</span>
                </div>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
              <div className="p-4 font-mono text-sm">
                <div className="text-gray-500">&lt;!-- Add this before &lt;/body&gt; --&gt;</div>
                <div className="mt-1">
                  <span className="text-gray-500">&lt;</span>
                  <span className="text-red-400">script</span>
                  <span className="text-blue-400"> src</span>
                  <span className="text-gray-400">=</span>
                  <span className="text-green-400">"https://app.voiceflow.ai/api/widget/YOUR_AGENT_ID/embed.js"</span>
                  <span className="text-gray-500">&gt;&lt;/</span>
                  <span className="text-red-400">script</span>
                  <span className="text-gray-500">&gt;</span>
                </div>
              </div>
            </div>

            {/* Mock widget preview */}
            <div className="rounded-xl border border-gray-700 bg-gray-950/50 p-4 space-y-3">
              <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">What your visitors see</p>
              <div className="bg-white rounded-lg p-4 space-y-3 shadow-inner">
                <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">Your AI Assistant</p>
                    <p className="text-xs text-green-600">Online</p>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg rounded-tl-none px-3 py-2 max-w-[80%]">
                      <p className="text-sm text-gray-800">Hi! How can I help you today? I know everything about your company.</p>
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <div className="bg-blue-600 rounded-lg rounded-tr-none px-3 py-2 max-w-[80%]">
                      <p className="text-sm text-white">What are your pricing plans?</p>
                    </div>
                  </div>
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg rounded-tl-none px-3 py-2 max-w-[80%]">
                      <p className="text-sm text-gray-800">We offer three plans: Starter at $99/mo, Professional at $299/mo, and custom Enterprise. Would you like details on any of these?</p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-1 border-t border-gray-100">
                  <div className="flex-1 h-9 rounded-lg bg-gray-50 border border-gray-200 px-3 flex items-center">
                    <span className="text-xs text-gray-400">Type a message…</span>
                  </div>
                  <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-white" />
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
