import React, { useState } from 'react';
import { Phone, MessageSquare, Hash, Slack } from 'lucide-react';
import { Button } from '../../ui/Button';
import { Input } from '../../ui/Input';

const channelOptions = [
  {
    id: 'phone',
    title: 'Phone Number',
    description: 'Dedicated phone line for voice calls',
    icon: <Phone className="h-6 w-6" />,
    setup: true
  },
  {
    id: 'chat',
    title: 'Website Chat Widget',
    description: 'Embeddable chat widget for your website',
    icon: <MessageSquare className="h-6 w-6" />,
    setup: false
  },
  {
    id: 'whatsapp',
    title: 'WhatsApp Business',
    description: 'Connect via WhatsApp Business API',
    icon: <Hash className="h-6 w-6" />,
    setup: true
  },
  {
    id: 'slack',
    title: 'Slack Integration',
    description: 'Internal Slack bot for employees',
    icon: <Slack className="h-6 w-6" />,
    setup: true
  }
];

interface ChannelSetupProps {
  data: Record<string, any>;
  onDataChange: (data: Record<string, any>) => void;
  onNext: () => void;
}

export const ChannelSetup: React.FC<ChannelSetupProps> = ({ data, onDataChange, onNext }) => {
  const [selectedChannels, setSelectedChannels] = useState<string[]>(data.selectedChannels || ['phone']);
  const [phoneSetup, setPhoneSetup] = useState({
    preferredArea: data.phoneSetup?.preferredArea || '',
    businessHours: data.phoneSetup?.businessHours || 'business',
    ...data.phoneSetup
  });

  const toggleChannel = (channelId: string) => {
    setSelectedChannels(prev => 
      prev.includes(channelId)
        ? prev.filter(id => id !== channelId)
        : [...prev, channelId]
    );
  };

  const handleNext = () => {
    onDataChange({
      selectedChannels,
      phoneSetup
    });
    onNext();
  };

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Setup communication channels</h2>
        <p className="text-gray-600">Choose how customers will interact with your AI agent</p>
      </div>

      {/* Channel Selection */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Available Channels</h3>
        
        <div className="grid md:grid-cols-2 gap-4">
          {channelOptions.map(channel => (
            <label
              key={channel.id}
              className={`flex items-start p-4 rounded-xl border-2 cursor-pointer transition-all ${
                selectedChannels.includes(channel.id)
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <input
                type="checkbox"
                checked={selectedChannels.includes(channel.id)}
                onChange={() => toggleChannel(channel.id)}
                className="sr-only"
              />
              <div className="flex items-start space-x-3">
                <div className={`p-2 rounded-lg ${
                  selectedChannels.includes(channel.id) 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-100 text-gray-600'
                }`}>
                  {channel.icon}
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900">{channel.title}</h4>
                  <p className="text-sm text-gray-600">{channel.description}</p>
                  {channel.setup && selectedChannels.includes(channel.id) && (
                    <span className="inline-block mt-2 text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full">
                      Setup required
                    </span>
                  )}
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Phone Setup */}
      {selectedChannels.includes('phone') && (
        <div className="bg-gray-50 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Phone className="h-5 w-5 mr-2" />
            Phone Number Configuration
          </h3>
          
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <Input
                label="Preferred Area Code"
                type="text"
                value={phoneSetup.preferredArea}
                onChange={(e) => setPhoneSetup(prev => ({ ...prev, preferredArea: e.target.value }))}
                placeholder="e.g., 415, 212, 555"
              />
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Business Hours</label>
                <select
                  value={phoneSetup.businessHours}
                  onChange={(e) => setPhoneSetup(prev => ({ ...prev, businessHours: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="24/7">24/7 Availability</option>
                  <option value="business">Business Hours Only</option>
                  <option value="custom">Custom Schedule</option>
                </select>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 mb-1">Phone Number Assignment</h4>
              <p className="text-sm text-blue-700">
                We'll automatically assign you a dedicated phone number based on your preferences. 
                You can request changes after setup if needed.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Chat Widget Preview */}
      {selectedChannels.includes('chat') && (
        <div className="bg-gray-50 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Chat Widget Preview</h3>
          <div className="bg-white rounded-lg shadow-sm border p-4 max-w-sm">
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <MessageSquare className="h-4 w-4 text-white" />
              </div>
              <div>
                <div className="font-medium text-gray-900">AI Assistant</div>
                <div className="text-xs text-green-600">Online</div>
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-sm text-gray-700">
                Hi! I'm here to help. How can I assist you today?
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end pt-6">
        <Button 
          onClick={handleNext}
          disabled={selectedChannels.length === 0}
        >
          Continue to Testing
        </Button>
      </div>
    </div>
  );
};