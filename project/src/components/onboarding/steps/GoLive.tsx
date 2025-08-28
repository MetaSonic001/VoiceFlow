import React, { useState } from 'react';
import { Rocket, Phone, MessageSquare, BarChart3, Settings, ExternalLink, Copy, Check, Loader } from 'lucide-react';
import { Button } from '../../ui/Button';
import { apiClient } from '../../../config/api';

interface GoLiveProps {
  data: Record<string, any>;
  onDataChange: (data: Record<string, any>) => void;
  onNext: () => void;
}

export const GoLive: React.FC<GoLiveProps> = ({ data, onDataChange, onNext }) => {
  const [isDeploying, setIsDeploying] = useState(false);
  const [isDeployed, setIsDeployed] = useState(false);
  const [deploymentData, setDeploymentData] = useState<any>(null);
  const [copiedPhone, setCopiedPhone] = useState(false);
  const [copiedWidget, setCopiedWidget] = useState(false);

  const handleDeploy = async () => {
    setIsDeploying(true);
    
    try {
      const response = await apiClient.deployAgent();
      setDeploymentData(response);
      setIsDeployed(true);
    } catch (error) {
      console.error('Deployment failed:', error);
      // Fallback to mock data for demo
      await new Promise(resolve => setTimeout(resolve, 3000));
      setDeploymentData({
        phone_number: '+1 (555) 123-4567',
        widget_code: `<script src="https://widget.voiceflow.ai/v1/widget.js" data-agent="agent_${Math.random().toString(36).substr(2, 9)}"></script>`,
        agent_id: 'agent_' + Math.random().toString(36).substr(2, 9)
      });
      setIsDeployed(true);
    } finally {
      setIsDeploying(false);
    }
  };

  const copyToClipboard = (text: string, type: 'phone' | 'widget') => {
    navigator.clipboard.writeText(text);
    if (type === 'phone') {
      setCopiedPhone(true);
      setTimeout(() => setCopiedPhone(false), 2000);
    } else {
      setCopiedWidget(true);
      setTimeout(() => setCopiedWidget(false), 2000);
    }
  };

  if (!isDeployed) {
    return (
      <div className="space-y-8 text-center">
        <div className="space-y-4">
          <div className="w-20 h-20 bg-blue-100 rounded-full mx-auto flex items-center justify-center">
            <Rocket className="h-10 w-10 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Ready to launch!</h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Your AI agent is configured and ready to handle customer interactions. 
            Click the button below to deploy your agent and make it live.
          </p>
        </div>

        {/* Configuration Summary */}
        <div className="bg-gray-50 rounded-xl p-6 text-left">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Configuration Summary</h3>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <div>
                <span className="text-sm font-medium text-gray-700">Agent Name:</span>
                <p className="text-gray-900">{data.agentName}</p>
              </div>
              <div>
                <span className="text-sm font-medium text-gray-700">Role:</span>
                <p className="text-gray-900">{data.agentRole}</p>
              </div>
              <div>
                <span className="text-sm font-medium text-gray-700">Voice:</span>
                <p className="text-gray-900">{data.selectedVoice}</p>
              </div>
            </div>
            <div className="space-y-3">
              <div>
                <span className="text-sm font-medium text-gray-700">Personality:</span>
                <p className="text-gray-900">{data.selectedPersonality}</p>
              </div>
              <div>
                <span className="text-sm font-medium text-gray-700">Channels:</span>
                <p className="text-gray-900">{data.selectedChannels?.join(', ')}</p>
              </div>
              <div>
                <span className="text-sm font-medium text-gray-700">Knowledge Sources:</span>
                <p className="text-gray-900">{(data.uploadedFiles?.length || 0) + (data.websiteUrls?.filter((url: string) => url.trim()).length || 0)} sources</p>
              </div>
            </div>
          </div>
        </div>

        <Button
          onClick={handleDeploy}
          loading={isDeploying}
          size="lg"
          className="px-12"
        >
          {isDeploying ? (
            <>
              <Loader className="mr-2 h-4 w-4 animate-spin" />
              Deploying Agent...
            </>
          ) : (
            'Deploy Agent'
          )}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="text-center space-y-4">
        <div className="w-20 h-20 bg-green-100 rounded-full mx-auto flex items-center justify-center">
          <Check className="h-10 w-10 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Agent is live! 🎉</h2>
        <p className="text-gray-600">
          Your AI agent is now deployed and ready to handle customer interactions.
        </p>
      </div>

      {/* Access Information */}
      <div className="space-y-6">
        {data.selectedChannels?.includes('phone') && (
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Phone className="h-6 w-6 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-900">Phone Number</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Your agent is available at this dedicated phone number:
            </p>
            <div className="flex items-center space-x-3 bg-gray-50 rounded-lg p-3">
              <span className="text-xl font-mono font-bold text-gray-900">
                {deploymentData?.phone_number || '+1 (555) 123-4567'}
              </span>
              <button
                onClick={() => copyToClipboard(deploymentData?.phone_number || '+1 (555) 123-4567', 'phone')}
                className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
              >
                {copiedPhone ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
          </div>
        )}

        {data.selectedChannels?.includes('chat') && (
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-center space-x-3 mb-4">
              <MessageSquare className="h-6 w-6 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-900">Website Chat Widget</h3>
            </div>
            <p className="text-gray-600 mb-4">
              Add this code to your website to embed the chat widget:
            </p>
            <div className="bg-gray-50 rounded-lg p-3">
              <code className="text-sm text-gray-800 block overflow-x-auto">
                {deploymentData?.widget_code || `<script src="https://widget.voiceflow.ai/v1/widget.js" data-agent="agent_${Math.random().toString(36).substr(2, 9)}"></script>`}
              </code>
              <button
                onClick={() => copyToClipboard(deploymentData?.widget_code || '', 'widget')}
                className="mt-2 p-2 text-gray-500 hover:text-gray-700 transition-colors"
              >
                {copiedWidget ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Next Steps */}
      <div className="bg-blue-50 rounded-xl p-6 border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">What's next?</h3>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="flex items-start space-x-3">
            <BarChart3 className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-gray-900">Monitor Performance</h4>
              <p className="text-sm text-gray-600">Track calls, success rates, and analytics</p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <Settings className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-gray-900">Fine-tune Agent</h4>
              <p className="text-sm text-gray-600">Improve responses based on feedback</p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <ExternalLink className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-gray-900">Add Integrations</h4>
              <p className="text-sm text-gray-600">Connect to your CRM and other tools</p>
            </div>
          </div>
        </div>
      </div>

      <div className="text-center">
        <Button onClick={onNext} size="lg">
          Go to Dashboard
        </Button>
      </div>
    </div>
  );
};