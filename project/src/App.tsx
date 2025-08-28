import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Header } from './components/layout/Header';
import { Hero } from './components/landing/Hero';
import { Features } from './components/landing/Features';
import { Pricing } from './components/landing/Pricing';
import { AuthModal } from './components/auth/AuthModal';
import { OnboardingWizard } from './components/onboarding/OnboardingWizard';
import { Dashboard } from './components/dashboard/Dashboard';

const AppContent: React.FC = () => {
  const { user, loading } = useAuth();
  const [authModal, setAuthModal] = useState<{ isOpen: boolean; mode: 'login' | 'signup' }>({
    isOpen: false,
    mode: 'login'
  });
  const [showOnboarding, setShowOnboarding] = useState(false);

  const openAuthModal = (mode: 'login' | 'signup') => {
    setAuthModal({ isOpen: true, mode });
  };

  const closeAuthModal = () => {
    setAuthModal({ isOpen: false, mode: 'login' });
  };

  const handleGetStarted = () => {
    if (user) {
      setShowOnboarding(true);
    } else {
      openAuthModal('signup');
    }
  };

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
  };

  const handleCreateAgent = () => {
    setShowOnboarding(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-pulse">
          <div className="w-8 h-8 bg-blue-600 rounded-full animate-bounce"></div>
        </div>
      </div>
    );
  }

  // Show onboarding wizard
  if (user && showOnboarding) {
    return (
      <OnboardingWizard onComplete={handleOnboardingComplete} />
    );
  }

  // Show dashboard for logged in users
  if (user && !showOnboarding) {
    return (
      <Dashboard onCreateAgent={handleCreateAgent} />
    );
  }

  // Show landing page for non-authenticated users
  return (
    <div className="min-h-screen bg-white">
      <Header
        onLoginClick={() => openAuthModal('login')}
        onSignupClick={() => openAuthModal('signup')}
      />
      
      <Hero onGetStarted={handleGetStarted} />
      <Features />
      <Pricing onGetStarted={handleGetStarted} />

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-4">
            <h3 className="text-2xl font-bold">VoiceFlow AI</h3>
            <p className="text-gray-400">
              Build, deploy, and manage intelligent voice agents in minutes
            </p>
            <div className="pt-8 border-t border-gray-800">
              <p className="text-gray-500">
                © 2024 VoiceFlow AI. All rights reserved.
              </p>
            </div>
          </div>
        </div>
      </footer>

      <AuthModal
        isOpen={authModal.isOpen}
        onClose={closeAuthModal}
        mode={authModal.mode}
      />
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;