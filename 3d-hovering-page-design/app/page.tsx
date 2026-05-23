'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import ComputerScene from '@/components/computer-scene';
import { LandingNavbar } from '@/components/landing-navbar';

export default function Home() {
  const [mouseX, setMouseX] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const centerX = rect.width / 2;
        const mousePos = e.clientX - rect.left;
        // Normalize to -1 to 1 range
        const normalizedX = (mousePos - centerX) / (centerX * 0.5);
        setMouseX(Math.max(-1, Math.min(1, normalizedX)));
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <>
      <LandingNavbar />
      <div ref={containerRef} className="min-h-screen bg-stone-100 flex items-center justify-between px-12 py-20 pt-24">
      {/* Left side - Text content */}
      <div className="flex-1 max-w-md">
        <h1 className="font-serif text-7xl mb-8 text-stone-900">
          Introducing<br />
          <span className="italic">Fig Mint.</span>
        </h1>

        <p className="font-serif text-lg leading-relaxed text-stone-700 mb-12">
          Not a figment of your imagination. Fig Mint thinks, drafts your memos, organizes your files, and learns how you work. The future of personal computing is here. And it fits on your desk.
        </p>

        <div className="flex items-center gap-6 mb-16">
          <Link href="/dashboard" className="inline-block">
            <button className="bg-stone-900 text-white px-8 py-4 rounded-lg font-serif text-lg hover:bg-stone-800 transition-colors">
              Get Started with VoiceFlow
            </button>
          </Link>
          <span className="font-mono text-xl text-stone-900">Try for Free</span>
        </div>

        {/* Specs */}
        <div className="grid grid-cols-2 gap-8 text-sm">
          <div>
            <div className="font-sans font-bold text-stone-900 uppercase tracking-wider text-xs mb-2">Processor</div>
            <div className="font-mono text-stone-700">Neural Engine</div>
          </div>
          <div>
            <div className="font-sans font-bold text-stone-900 uppercase tracking-wider text-xs mb-2">Memory</div>
            <div className="font-mono text-stone-700">512K Synapse</div>
          </div>
          <div>
            <div className="font-sans font-bold text-stone-900 uppercase tracking-wider text-xs mb-2">Storage</div>
            <div className="font-mono text-stone-700">5.25" Floppy</div>
          </div>
          <div>
            <div className="font-sans font-bold text-stone-900 uppercase tracking-wider text-xs mb-2">Display</div>
            <div className="font-mono text-stone-700">9" Phosphor</div>
          </div>
        </div>
      </div>

      {/* Right side - 3D Computer */}
      <div className="flex-1 flex justify-center items-center h-96">
        <ComputerScene mouseX={mouseX} />
      </div>
    </div>
    </>
  );
}
