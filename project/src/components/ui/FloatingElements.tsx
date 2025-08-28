import React from 'react';
import { motion } from 'framer-motion';
import { Phone, MessageSquare, Bot, Zap, Shield, Globe } from 'lucide-react';

const icons = [Phone, MessageSquare, Bot, Zap, Shield, Globe];

export const FloatingElements: React.FC = () => {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {icons.map((Icon, index) => (
        <motion.div
          key={index}
          className="absolute"
          style={{
            left: `${10 + (index * 15)}%`,
            top: `${20 + (index * 10)}%`,
          }}
          animate={{
            y: [-20, 20, -20],
            rotate: [0, 360],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 4 + index,
            repeat: Infinity,
            ease: "easeInOut",
            delay: index * 0.5,
          }}
        >
          <div className="w-12 h-12 bg-white/10 backdrop-blur-sm rounded-full flex items-center justify-center border border-white/20">
            <Icon className="w-6 h-6 text-blue-300" />
          </div>
        </motion.div>
      ))}
    </div>
  );
};