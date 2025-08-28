import React, { useState } from 'react';
import { Volume2, User, MessageCircle, Play, Pause } from 'lucide-react';
import { Button } from '../../ui/Button';

const voiceOptions = [
  { id: 'sarah', name: 'Sarah', gender: 'Female', accent: 'American', description: 'Professional and friendly' },
  { id: 'alex', name: 'Alex', gender: 'Male', accent: 'American', description: 'Confident and approachable' },
  { id: 'emma', name: 'Emma', gender: 'Female', accent: 'British', description: 'Elegant and articulate' },
  { id: 'james', name: 'James', gender: 'Male', accent: 'British', description: 'Authoritative and calm' },
];

const personalityOptions = [
  { id: 'professional', title: 'Professional', description: 'Formal, precise, and business-focused' },
  { id: 'friendly', title: 'Friendly', description: 'Warm, conversational, and approachable' },
  { id: 'empathetic', title: 'Empathetic', description: 'Understanding, supportive, and caring' },
  { id: 'sales-driven', title: 'Sales-Driven', description: 'Persuasive, enthusiastic, and goal-oriented' },
];

interface VoicePersonalityProps {
  data: Record<string, any>;
  onDataChange: (data: Record<string, any>) => void;
  onNext: () => void;
}

export const VoicePersonality: React.FC<VoicePersonalityProps> = ({ data, onDataChange, onNext }) => {
  const [selectedVoice, setSelectedVoice] = useState(data.selectedVoice || '');
  const [selectedPersonality, setSelectedPersonality] = useState(data.selectedPersonality || '');
  const [customInstructions, setCustomInstructions] = useState(data.customInstructions || '');
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);

  const handleVoicePlay = (voiceId: string) => {
    if (playingVoice === voiceId) {
      setPlayingVoice(null);
    } else {
      setPlayingVoice(voiceId);
      // Simulate audio playback
      setTimeout(() => setPlayingVoice(null), 3000);
    }
  };

  const handleNext = () => {
    onDataChange({
      selectedVoice,
      selectedPersonality,
      customInstructions
    });
    onNext();
  };

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Choose voice & personality</h2>
        <p className="text-gray-600">Configure how your agent sounds and behaves during conversations</p>
      </div>

      {/* Voice Selection */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <Volume2 className="h-5 w-5 mr-2" />
          Voice Selection
        </h3>
        
        <div className="grid md:grid-cols-2 gap-4">
          {voiceOptions.map(voice => (
            <div
              key={voice.id}
              className={`border-2 rounded-xl p-4 cursor-pointer transition-all ${
                selectedVoice === voice.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setSelectedVoice(voice.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <User className="h-4 w-4 text-gray-500" />
                    <span className="font-semibold text-gray-900">{voice.name}</span>
                    <span className="text-sm text-gray-500">({voice.gender})</span>
                  </div>
                  <p className="text-sm text-gray-600">{voice.description}</p>
                  <p className="text-xs text-gray-500">{voice.accent} accent</p>
                </div>
                
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleVoicePlay(voice.id);
                  }}
                  className="ml-4 p-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  {playingVoice === voice.id ? (
                    <Pause className="h-4 w-4" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Personality Selection */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <MessageCircle className="h-5 w-5 mr-2" />
          Personality & Tone
        </h3>
        
        <div className="grid md:grid-cols-2 gap-4">
          {personalityOptions.map(personality => (
            <label
              key={personality.id}
              className={`flex items-start p-4 rounded-xl border-2 cursor-pointer transition-all ${
                selectedPersonality === personality.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <input
                type="radio"
                name="personality"
                value={personality.id}
                checked={selectedPersonality === personality.id}
                onChange={(e) => setSelectedPersonality(e.target.value)}
                className="sr-only"
              />
              <div>
                <h4 className="font-semibold text-gray-900 mb-1">{personality.title}</h4>
                <p className="text-sm text-gray-600">{personality.description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Custom Instructions */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Custom Instructions (Optional)</h3>
        <textarea
          value={customInstructions}
          onChange={(e) => setCustomInstructions(e.target.value)}
          placeholder="Add specific guidelines for how your agent should behave, what it should say, or any special instructions..."
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          rows={4}
        />
      </div>

      {/* Preview */}
      {(selectedVoice && selectedPersonality) && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200">
          <h4 className="font-semibold text-gray-900 mb-3">Preview Configuration</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center space-x-2">
              <Volume2 className="h-4 w-4 text-blue-600" />
              <span><strong>Voice:</strong> {voiceOptions.find(v => v.id === selectedVoice)?.name}</span>
            </div>
            <div className="flex items-center space-x-2">
              <MessageCircle className="h-4 w-4 text-blue-600" />
              <span><strong>Personality:</strong> {personalityOptions.find(p => p.id === selectedPersonality)?.title}</span>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end pt-6">
        <Button 
          onClick={handleNext}
          disabled={!selectedVoice || !selectedPersonality}
        >
          Continue to Channel Setup
        </Button>
      </div>
    </div>
  );
};