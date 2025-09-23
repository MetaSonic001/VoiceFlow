import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Button } from './ui/button';
import { PlayCircle, ArrowRight, Zap, Shield, Globe, HelpCircle } from 'lucide-react';
import { TypewriterEffect } from './ui/TypewriterEffect';
import { AnimatedBackground } from './ui/AnimatedBackground';
import { FloatingElements } from './ui/FloatingElements';
import { HelpModal } from './ui/HelpModal';

interface HeroProps {
  onGetStarted: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onGetStarted }) => {
  const [showHelp, setShowHelp] = useState(false);

  const typewriterWords = [
    "customer support",
    "sales calls", 
    "appointment booking",
    "lead qualification",
    "technical support"
  ];

  return (
    <section className="relative bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 py-20 lg:py-32 overflow-hidden">
      <AnimatedBackground />
      <FloatingElements />
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <motion.div 
            className="space-y-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="space-y-6">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 }}
                className="inline-flex items-center px-4 py-2 rounded-full bg-blue-100 text-blue-700 text-sm font-medium border border-blue-200"
              >
                <Zap className="h-4 w-4 mr-2" />
                Enterprise-Grade AI Voice Agents
              </motion.div>
              
              <h1 className="text-4xl lg:text-6xl font-bold text-gray-900 leading-tight">
                Automate{' '}
                <TypewriterEffect 
                  words={typewriterWords}
                  className="text-blue-600"
                />
                <br />
                with intelligent AI agents
              </h1>
              
              <p className="text-xl text-gray-600 leading-relaxed max-w-2xl">
                Deploy human-like AI voice agents that handle customer interactions 24/7. 
                Reduce costs by 80% while improving customer satisfaction and response times.
              </p>
            </div>

            <motion.div 
              className="flex flex-col sm:flex-row gap-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <Button size="lg" onClick={onGetStarted} className="group bg-blue-600 hover:bg-blue-700">
                Start Building Now
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Button>
              
              <Button variant="outline" size="lg" className="group border-gray-300">
                <PlayCircle className="mr-2 h-5 w-5" />
                Watch Demo
              </Button>
              
              <Button 
                variant="ghost" 
                size="lg" 
                onClick={() => setShowHelp(true)}
                className="group text-blue-600 hover:text-blue-700"
              >
                <HelpCircle className="mr-2 h-5 w-5" />
                How it works
              </Button>
            </motion.div>

            <motion.div 
              className="flex items-center space-x-8 text-sm text-gray-600"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
            >
              <div className="flex items-center">
                <Shield className="h-4 w-4 mr-2 text-green-500" />
                SOC 2 Compliant
              </div>
              <div className="flex items-center">
                <Globe className="h-4 w-4 mr-2 text-blue-500" />
                40+ Languages
              </div>
              <div className="flex items-center">
                <Zap className="h-4 w-4 mr-2 text-purple-500" />
                99.9% Uptime
              </div>
            </motion.div>
          </motion.div>

          <motion.div 
            className="relative"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <div className="relative bg-white rounded-2xl shadow-2xl p-8 border border-gray-200">
              <motion.div 
                className="space-y-6"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
              >
                <div className="flex items-center space-x-3">
                  <motion.div 
                    className="w-3 h-3 bg-green-500 rounded-full"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                  <span className="text-gray-900 font-medium">AI Agent is active</span>
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">LIVE</span>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4 border-l-4 border-blue-500">
                  <p className="text-gray-700 text-sm">
                    "Hello! I'm Sarah from TechCorp's support team. I can help you with account questions, 
                    billing inquiries, or technical issues. How can I assist you today?"
                  </p>
                </div>

                <div className="flex justify-between text-sm text-gray-500 bg-gray-50 rounded-lg p-3">
                  <span>Response time: 0.3s</span>
                  <span>Confidence: 99.2%</span>
                  <span>Language: English</span>
                </div>

                <div className="grid grid-cols-3 gap-4 text-sm">
                  <motion.div 
                    className="bg-blue-50 rounded-lg p-3 text-center"
                    whileHover={{ scale: 1.05 }}
                  >
                    <div className="text-blue-700 font-medium">Calls Today</div>
                    <div className="text-2xl font-bold text-blue-600">1,247</div>
                  </motion.div>
                  <motion.div 
                    className="bg-emerald-50 rounded-lg p-3 text-center"
                    whileHover={{ scale: 1.05 }}
                  >
                    <div className="text-emerald-700 font-medium">Success Rate</div>
                    <div className="text-2xl font-bold text-emerald-600">96.8%</div>
                  </motion.div>
                  <motion.div 
                    className="bg-purple-50 rounded-lg p-3 text-center"
                    whileHover={{ scale: 1.05 }}
                  >
                    <div className="text-purple-700 font-medium">Avg Duration</div>
                    <div className="text-2xl font-bold text-purple-600">2m 15s</div>
                  </motion.div>
                </div>
              </motion.div>

              {/* Decorative elements */}
              <motion.div 
                className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-blue-400 to-purple-600 rounded-full opacity-20"
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              />
              <motion.div 
                className="absolute -bottom-4 -left-4 w-32 h-32 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-full opacity-20"
                animate={{ rotate: -360 }}
                transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
              />
            </div>
          </motion.div>
        </div>
      </div>

      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
    </section>
  );
};