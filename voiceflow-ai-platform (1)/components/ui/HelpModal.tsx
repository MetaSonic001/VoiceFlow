import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowRight, CheckCircle } from 'lucide-react';
import { Button } from './Button';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const steps = [
  {
    title: "Sign Up & Company Setup",
    description: "Create your account and tell us about your business",
    icon: "1"
  },
  {
    title: "Create Your AI Agent",
    description: "Define your agent's role, personality, and capabilities",
    icon: "2"
  },
  {
    title: "Upload Knowledge Base",
    description: "Add documents, FAQs, and training materials",
    icon: "3"
  },
  {
    title: "Configure Voice & Channels",
    description: "Choose voice style and setup communication channels",
    icon: "4"
  },
  {
    title: "Test & Deploy",
    description: "Test your agent and deploy it live to start handling calls",
    icon: "5"
  }
];

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">How VoiceFlow AI Works</h2>
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              <p className="text-gray-600 mt-2">
                Get your AI voice agent up and running in just 5 simple steps
              </p>
            </div>

            <div className="p-6">
              <div className="space-y-6">
                {steps.map((step, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-start space-x-4"
                  >
                    <div className="flex-shrink-0 w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-semibold">
                      {step.icon}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        {step.title}
                      </h3>
                      <p className="text-gray-600">{step.description}</p>
                    </div>
                    {index < steps.length - 1 && (
                      <ArrowRight className="w-5 h-5 text-gray-400 mt-2" />
                    )}
                  </motion.div>
                ))}
              </div>

              <div className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-start space-x-3">
                  <CheckCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-blue-900">Ready to get started?</h4>
                    <p className="text-blue-700 text-sm mt-1">
                      The entire setup process takes less than 10 minutes. Your AI agent will be ready to handle customer calls immediately after deployment.
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <Button onClick={onClose}>
                  Got it, let's start!
                </Button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};