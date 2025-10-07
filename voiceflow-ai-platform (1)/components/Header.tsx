import React from 'react';
import MotionWrapper from './ui/MotionWrapper'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from './ui/button';
import { Mic, Menu, X } from 'lucide-react';

interface HeaderProps {
  onLoginClick: () => void;
  onSignupClick: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onLoginClick, onSignupClick }) => {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);

  return (
    <MotionWrapper>
      <header className="bg-white/95 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-br from-blue-600 to-purple-600 p-2 rounded-lg">
                <Mic className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">VoiceFlow AI</span>
            </div>
          </div>

          <nav className="hidden md:flex items-center space-x-8" aria-label="Main navigation">
            {['Features', 'Pricing', 'Solutions', 'Resources'].map((item, index) => (
              <motion.a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="text-gray-600 hover:text-gray-900 transition-colors font-medium"
                whileHover={{ scale: 1.05 }}
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                {item}
              </motion.a>
            ))}
          </nav>

          <div className="hidden md:flex items-center space-x-4">
            <Button variant="ghost" onClick={onLoginClick}>
              Sign In
            </Button>
            <Button onClick={onSignupClick} className="bg-blue-600 hover:bg-blue-700">
              Get Started Free
            </Button>
          </div>

          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
          <AnimatePresence>
          {isMenuOpen && (
          <motion.div 
            className="md:hidden py-4 border-t border-gray-200"
            initial={{ opacity: 0, height: 0, y: -6 }}
            animate={{ opacity: 1, height: 'auto', y: 0 }}
            exit={{ opacity: 0, height: 0, y: -6 }}
            transition={{ duration: 0.28, ease: 'easeOut' }}
          >
            <div className="flex flex-col space-y-4">
              {['Features', 'Pricing', 'Solutions', 'Resources'].map((item) => (
                <a
                  key={item}
                  href={`#${item.toLowerCase()}`}
                  className="text-gray-600 hover:text-gray-900 transition-colors font-medium"
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item}
                </a>
              ))}
              <div className="flex flex-col space-y-2 pt-4 border-t border-gray-200">
                <Button variant="ghost" onClick={onLoginClick} className="justify-start">
                  Sign In
                </Button>
                <Button onClick={onSignupClick} className="justify-start bg-blue-600 hover:bg-blue-700">
                  Get Started Free
                </Button>
              </div>
            </div>
          </motion.div>
          )}
          </AnimatePresence>
      </div>
      </header>
    </MotionWrapper>
  );
};