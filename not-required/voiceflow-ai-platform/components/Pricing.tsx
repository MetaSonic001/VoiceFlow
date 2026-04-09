import React from 'react';
import { motion } from 'framer-motion';
import { Button } from './ui/button';
import FeatureCard from './ui/FeatureCard';
import { Check, ArrowRight, Star, Zap } from 'lucide-react';

const plans = [
  {
    name: 'Starter',
    price: 99,
    originalPrice: 149,
    description: 'Perfect for small businesses getting started',
    popular: false,
    features: [
      '1 AI agent',
      '1,000 minutes/month',
      'Basic voice options',
      'Chat widget integration',
      'Email support',
      'Basic analytics',
      'Phone number included'
    ],
    indianPrice: '₹8,299',
    indianOriginalPrice: '₹12,499'
  },
  {
    name: 'Professional',
    price: 299,
    originalPrice: 399,
    description: 'For growing teams and businesses',
    popular: true,
    features: [
      '5 AI agents',
      '5,000 minutes/month',
      'Premium voices',
      'Multi-channel support',
      'Priority support',
      'Advanced analytics',
      'CRM integrations',
      'Custom branding',
      'API access'
    ],
    indianPrice: '₹24,999',
    indianOriginalPrice: '₹33,499'
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    description: 'For large organizations with custom needs',
    popular: false,
    features: [
      'Unlimited agents',
      'Unlimited minutes',
      'Custom voice training',
      'White-label solution',
      'Dedicated support',
      'Custom integrations',
      'SLA guarantees',
      'Advanced security',
      'On-premise deployment'
    ],
    indianPrice: 'Custom',
    cta: 'Contact Sales'
  }
];

interface PricingProps {
  onGetStarted: () => void;
}

export const Pricing: React.FC<PricingProps> = ({ onGetStarted }) => {
  const [isIndianPricing, setIsIndianPricing] = React.useState(false);

  return (
    <section id="pricing" className="py-20 bg-gradient-to-br from-gray-50 to-blue-50 relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(59,130,246,0.1),transparent_50%)]"></div>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_80%,rgba(147,51,234,0.1),transparent_50%)]"></div>
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div 
          className="text-center space-y-4 mb-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-3xl lg:text-4xl font-bold text-gray-900">
            Simple, transparent pricing
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Choose the plan that fits your needs. All plans include our core features and can be upgraded anytime.
          </p>
          
          {/* Pricing Toggle */}
          <div className="flex items-center justify-center space-x-4 mt-8">
            <span className={`text-sm font-medium ${!isIndianPricing ? 'text-gray-900' : 'text-gray-500'}`}>
              USD Pricing
            </span>
            <button
              onClick={() => setIsIndianPricing(!isIndianPricing)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                isIndianPricing ? 'bg-blue-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isIndianPricing ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <span className={`text-sm font-medium ${isIndianPricing ? 'text-gray-900' : 'text-gray-500'}`}>
              Indian Pricing
            </span>
          </div>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          {plans.map((plan, index) => (
            <motion.div 
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.08 }}
            >
              <FeatureCard title={plan.name} icon={<Star className="w-5 h-5 text-yellow-500" />}>
                <div>
                  <div className="text-2xl font-bold text-gray-900 mb-2">{typeof plan.price === 'number' ? (isIndianPricing ? plan.indianPrice : `$${plan.price}`) : (isIndianPricing ? plan.indianPrice : plan.price)}</div>
                  <p className="text-sm text-gray-600 mb-3">{plan.description}</p>
                  <div className="text-sm text-gray-600 mb-4">
                    {plan.features.slice(0, 5).map((f, i) => <div key={i} className="flex items-center"><Check className="w-4 h-4 text-green-500 mr-2"/>{f}</div>)}
                  </div>
                  <Button onClick={onGetStarted} className="w-full mt-2 bg-blue-600 hover:bg-blue-700">{plan.cta || 'Start Free Trial'}</Button>
                </div>
              </FeatureCard>
            </motion.div>
          ))}
        </div>

        <motion.div 
          className="mt-16 text-center space-y-6"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <FeatureCard title={"🇮🇳 Special Launch Offer for Indian Businesses"} icon={<Zap className="w-5 h-5 text-blue-500"/>}>
            <p className="text-gray-600 mb-4">
              Get started with our Professional plan at a special introductory price. Perfect for Indian startups and SMEs looking to automate customer support.
            </p>
            <div className="flex items-center justify-center space-x-4 text-sm text-gray-600">
              <span>✅ 14-day free trial</span>
              <span>✅ No setup fees</span>
              <span>✅ Cancel anytime</span>
              <span>✅ Indian phone numbers</span>
            </div>
          </FeatureCard>

          <p className="text-gray-600">
            All plans include a 14-day free trial. No credit card required to get started.
          </p>
        </motion.div>
      </div>
    </section>
  );
};