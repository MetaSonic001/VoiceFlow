'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { ComputerSceneWrapper } from '@/components/landing/computer-scene-wrapper';
import { LandingNavbar } from '@/components/landing/landing-navbar';
import { FeaturesSection } from '@/components/landing/features-section';
import { DashboardPreviewSection } from '@/components/landing/dashboard-preview-section';
import { InteractiveAgentDemo } from '@/components/landing/interactive-agent-demo';
import { EmbedSection } from '@/components/landing/embed-section';
import { PricingSection } from '@/components/landing/pricing-section';
import { LandingFooter } from '@/components/landing/landing-footer';

export default function Home() {
  const [mouseX, setMouseX] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const centerX = rect.width / 2;
        const mousePos = e.clientX - rect.left;
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

      <section className="w-full bg-stone-100 lg:h-screen lg:min-h-[700px] flex items-center lg:overflow-hidden">
        <div
          ref={containerRef}
          className="w-full flex flex-col lg:flex-row items-center lg:items-center justify-between gap-12 lg:gap-8 px-8 py-20 pt-32 lg:py-0 lg:pt-28 max-w-7xl mx-auto h-full"
        >
          <div className="w-full lg:w-3/5 lg:pr-8">
            <h1 className="font-serif text-5xl sm:text-6xl lg:text-6xl xl:text-7xl mb-6 lg:mb-4 xl:mb-6 text-stone-900 tracking-tight leading-[1.1]">
              Introducing<br />
              <span className="italic">VoiceFlow.</span>
            </h1>

            <p className="font-serif text-lg leading-relaxed text-stone-700 mb-8 lg:mb-6 xl:mb-10 max-w-2xl">
              Build, deploy, and manage AI voice agents that handle customer interactions naturally — across phone, chat, and web. The future of voice automation is here.
            </p>

            <div className="flex items-center gap-8 mb-12 lg:mb-8 xl:mb-14">
              <Link href="/register" className="inline-block">
                <button className="bg-stone-900 text-white px-8 py-4 rounded-xl font-serif text-lg hover:bg-stone-800 transition-colors">
                  Get Started with VoiceFlow
                </button>
              </Link>
              <Link href="/login" className="font-serif text-xl text-stone-900 hover:text-stone-700 transition-colors">
                Try for Free
              </Link>
            </div>

            <div className="grid grid-cols-2 gap-x-12 gap-y-6 lg:gap-y-4 xl:gap-y-6 text-sm">
              <div>
                <div className="font-sans font-bold text-stone-955 uppercase tracking-wider text-xs mb-1.5">Processor</div>
                <div className="font-serif text-stone-800 text-base">Neural Engine</div>
              </div>
              <div>
                <div className="font-sans font-bold text-stone-955 uppercase tracking-wider text-xs mb-1.5">Memory</div>
                <div className="font-serif text-stone-800 text-base">512K Synapse</div>
              </div>
              <div>
                <div className="font-sans font-bold text-stone-955 uppercase tracking-wider text-xs mb-1.5">Storage</div>
                <div className="font-serif text-stone-800 text-base">5.25&quot; Floppy</div>
              </div>
              <div>
                <div className="font-sans font-bold text-stone-955 uppercase tracking-wider text-xs mb-1.5">Display</div>
                <div className="font-serif text-stone-800 text-base">9&quot; Phosphor</div>
              </div>
            </div>
          </div>

          <div className="w-full lg:w-2/5 flex justify-center items-center h-64 sm:h-80 lg:h-[400px] xl:h-[480px] lg:min-h-0 shrink-0">
            <div className="w-full h-full max-w-[320px] sm:max-w-[380px] lg:max-w-[400px] mx-auto">
              <ComputerSceneWrapper mouseX={mouseX} />
            </div>
          </div>
        </div>
      </section>

      <FeaturesSection />
      <DashboardPreviewSection />
      <InteractiveAgentDemo />
      <EmbedSection />
      <PricingSection />
      <LandingFooter />
    </>
  );
}
