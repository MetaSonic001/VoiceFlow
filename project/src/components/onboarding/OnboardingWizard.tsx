import React, { useState } from 'react';
import { ChevronRight, ChevronLeft, Check } from 'lucide-react';
import { Button } from '../ui/Button';
import { CompanySetup } from './steps/CompanySetup';
import { AgentCreation } from './steps/AgentCreation';
import { KnowledgeUpload } from './steps/KnowledgeUpload';
import { VoicePersonality } from './steps/VoicePersonality';
import { ChannelSetup } from './steps/ChannelSetup';
import { TestingSandbox } from './steps/TestingSandbox';
import { GoLive } from './steps/GoLive';
import { apiClient } from '../../config/api';

const steps = [
  { id: 'company', title: 'Company Profile', component: CompanySetup },
  { id: 'agent', title: 'Create Agent', component: AgentCreation },
  { id: 'knowledge', title: 'Upload Knowledge', component: KnowledgeUpload },
  { id: 'voice', title: 'Voice & Personality', component: VoicePersonality },
  { id: 'channels', title: 'Setup Channels', component: ChannelSetup },
  { id: 'testing', title: 'Test Agent', component: TestingSandbox },
  { id: 'live', title: 'Go Live', component: GoLive }
];

interface OnboardingWizardProps {
  onComplete: () => void;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [formData, setFormData] = useState<Record<string, any>>({});

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCompletedSteps(prev => [...prev, currentStep]);
      setCurrentStep(currentStep + 1);
    } else {
      // Create agent on completion
      apiClient.createAgent(formData).then(() => {
        onComplete();
      }).catch(error => {
        console.error('Agent creation failed:', error);
      });
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleStepData = (stepData: Record<string, any>) => {
    setFormData(prev => ({ ...prev, ...stepData }));
  };

  const CurrentStepComponent = steps[currentStep].component;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Progress Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900">Setup Your AI Agent</h1>
            <div className="text-sm text-gray-500">
              Step {currentStep + 1} of {steps.length}
            </div>
          </div>

          {/* Progress Steps */}
          <div className="flex items-center space-x-4 overflow-x-auto pb-2">
            {steps.map((step, index) => (
              <React.Fragment key={step.id}>
                <div className="flex items-center space-x-3 flex-shrink-0">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                      index < currentStep || completedSteps.includes(index)
                        ? 'bg-blue-600 text-white'
                        : index === currentStep
                        ? 'bg-blue-100 text-blue-600 border-2 border-blue-600'
                        : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {completedSteps.includes(index) ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      index + 1
                    )}
                  </div>
                  <div className="text-sm">
                    <div
                      className={`font-medium ${
                        index <= currentStep ? 'text-gray-900' : 'text-gray-500'
                      }`}
                    >
                      {step.title}
                    </div>
                  </div>
                </div>
                {index < steps.length - 1 && (
                  <ChevronRight className="h-4 w-4 text-gray-300 flex-shrink-0" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* Step Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border p-8">
          <CurrentStepComponent
            data={formData}
            onDataChange={handleStepData}
            onNext={handleNext}
            onPrevious={handlePrevious}
            canGoNext={true}
            canGoPrevious={currentStep > 0}
          />
        </div>
      </div>

      {/* Navigation */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentStep === 0}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Previous
          </Button>
          
          <Button onClick={handleNext}>
            {currentStep === steps.length - 1 ? 'Complete Setup' : 'Continue'}
            {currentStep < steps.length - 1 && <ChevronRight className="h-4 w-4 ml-2" />}
          </Button>
        </div>
      </div>
    </div>
  );
};