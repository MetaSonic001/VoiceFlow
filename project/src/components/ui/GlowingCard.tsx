import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../utils/cn';

interface GlowingCardProps {
  children: React.ReactNode;
  className?: string;
  glowColor?: string;
}

export const GlowingCard: React.FC<GlowingCardProps> = ({ 
  children, 
  className,
  glowColor = "blue"
}) => {
  return (
    <motion.div
      className={cn(
        "relative group",
        className
      )}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
    >
      <div className={`absolute -inset-0.5 bg-gradient-to-r from-${glowColor}-600 to-purple-600 rounded-lg blur opacity-0 group-hover:opacity-75 transition duration-1000 group-hover:duration-200`} />
      <div className="relative bg-white rounded-lg p-6 border border-gray-200">
        {children}
      </div>
    </motion.div>
  );
};