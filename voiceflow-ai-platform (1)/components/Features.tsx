import React from 'react';
import { motion } from 'framer-motion';
import { 
  Mic, 
  MessageSquare, 
  Brain, 
  Shield, 
  BarChart3, 
  Zap,
  Globe,
  Settings,
  Phone,
  Clock,
  Users,
  Target
} from 'lucide-react';
import FeatureCard from './ui/FeatureCard';

const features = [
  {
    icon: <Mic className="h-6 w-6" />,
    title: 'Human-like Voice AI',
    description: 'Natural conversations with advanced TTS and STT technology that sounds completely human.',
    color: 'blue'
  },
  {
    icon: <Brain className="h-6 w-6" />,
    title: 'Intelligent Understanding',
    description: 'Upload your documents and let AI agents understand your business context and processes.',
    color: 'purple'
  },
  {
    icon: <MessageSquare className="h-6 w-6" />,
    title: 'Multi-channel Support',
    description: 'Deploy across voice calls, chat widgets, WhatsApp, Slack, and other platforms.',
    color: 'green'
  },
  {
    icon: <Shield className="h-6 w-6" />,
    title: 'Enterprise Security',
    description: 'SOC 2 Type II compliant with end-to-end encryption and data privacy controls.',
    color: 'red'
  },
  {
    icon: <BarChart3 className="h-6 w-6" />,
    title: 'Advanced Analytics',
    description: 'Real-time insights on agent performance, conversation analytics, and ROI tracking.',
    color: 'indigo'
  },
  {
    icon: <Zap className="h-6 w-6" />,
    title: 'Instant Deployment',
    description: 'Go live in minutes with our one-click deployment and automated scaling.',
    color: 'yellow'
  },
  {
    icon: <Globe className="h-6 w-6" />,
    title: 'Global Reach',
    description: '40+ languages and regional voice options for worldwide customer support.',
    color: 'cyan'
  },
  {
    icon: <Settings className="h-6 w-6" />,
    title: 'Easy Customization',
    description: 'No coding required. Configure personality, responses, and workflows visually.',
    color: 'orange'
  },
  {
    icon: <Phone className="h-6 w-6" />,
    title: 'Smart Call Routing',
    description: 'Intelligent escalation to human agents when needed with full context transfer.',
    color: 'teal'
  }
];

const stats = [
  { icon: <Clock className="h-8 w-8" />, value: '0.3s', label: 'Average Response Time' },
  { icon: <Users className="h-8 w-8" />, value: '10M+', label: 'Conversations Handled' },
  { icon: <Target className="h-8 w-8" />, value: '96.8%', label: 'Customer Satisfaction' },
  { icon: <Zap className="h-8 w-8" />, value: '80%', label: 'Cost Reduction' }
];

export const Features: React.FC = () => {
  return (
    <section id="features" className="py-20 bg-white relative overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div 
          className="text-center space-y-4 mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl lg:text-4xl font-bold text-gray-900">
            Everything you need to automate conversations
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            From voice calls to chat widgets, our platform provides all the tools to create, 
            deploy, and manage intelligent conversational agents.
          </p>
        </motion.div>

        {/* Stats Section */}
        <motion.div 
          className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {stats.map((stat, index) => (
            <motion.div
              key={index}
              className="text-center p-6 bg-gradient-to-br from-gray-50 to-white rounded-xl border border-gray-200"
              whileHover={{ scale: 1.05 }}
              transition={{ duration: 0.2 }}
            >
              <div className="text-blue-600 mb-3 flex justify-center">
                {stat.icon}
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-1">{stat.value}</div>
              <div className="text-sm text-gray-600">{stat.label}</div>
            </motion.div>
          ))}
        </motion.div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.08 }}
            >
              <FeatureCard title={feature.title} icon={feature.icon}>
                {feature.description}
              </FeatureCard>
            </motion.div>
          ))}
        </div>

        {/* CTA Section */}
        <motion.div 
          className="mt-16 text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-8 text-white">
            <h3 className="text-2xl font-bold mb-4">Ready to transform your customer interactions?</h3>
            <p className="text-blue-100 mb-6 max-w-2xl mx-auto">
              Join thousands of businesses already using VoiceFlow AI to automate their customer support and sales processes.
            </p>
            <motion.button
              className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Start Your Free Trial
            </motion.button>
          </div>
        </motion.div>
      </div>
    </section>
  );
};