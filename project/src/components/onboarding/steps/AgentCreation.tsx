import React, { useState } from 'react';
import { Bot, User, Target, MessageSquare } from 'lucide-react';
import { Input } from '../../ui/Input';

const agentRoles = [
  {
    id: 'support',
    title: 'Customer Support',
    description: 'Handle customer inquiries, troubleshooting, and support tickets',
    icon: <MessageSquare className="h-6 w-6" />
  },
  {
    id: 'sales',
    title: 'Sales Assistant',
    description: 'Qualify leads, schedule demos, and support sales processes',
    icon: <Target className="h-6 w-6" />
  },
  {
    id: 'hr',
    title: 'HR Assistant',
    description: 'Handle employee queries, benefits, policies, and onboarding',
    icon: <User className="h-6 w-6" />
  },
  {
    id: 'receptionist',
    title: 'Virtual Receptionist',
    description: 'Route calls, schedule appointments, and provide basic information',
    icon: <Bot className="h-6 w-6" />
  }
];

interface AgentCreationProps {
  data: Record<string, any>;
  onDataChange: (data: Record<string, any>) => void;
  onNext: () => void;
}

export const AgentCreation: React.FC<AgentCreationProps> = ({ data, onDataChange, onNext }) => {
  const [formData, setFormData] = useState({
    agentName: data.agentName || '',
    agentRole: data.agentRole || '',
    agentDescription: data.agentDescription || '',
    ...data
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onDataChange(formData);
    onNext();
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const selectedRole = agentRoles.find(role => role.id === formData.agentRole);

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Create your AI agent</h2>
        <p className="text-gray-600">Give your agent a name and define its primary role</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Input
          label="Agent Name"
          type="text"
          value={formData.agentName}
          onChange={(e) => handleInputChange('agentName', e.target.value)}
          placeholder="e.g., Sarah, Alex, or CustomerBot"
          icon={<Bot className="h-5 w-5" />}
          required
        />

        <div className="space-y-4">
          <label className="block text-sm font-medium text-gray-700">Agent Role</label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agentRoles.map(role => (
              <label
                key={role.id}
                className={`flex items-start p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  formData.agentRole === role.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="agentRole"
                  value={role.id}
                  checked={formData.agentRole === role.id}
                  onChange={(e) => handleInputChange('agentRole', e.target.value)}
                  className="sr-only"
                />
                <div className="flex items-start space-x-3">
                  <div className={`p-2 rounded-lg ${
                    formData.agentRole === role.id ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {role.icon}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{role.title}</h3>
                    <p className="text-sm text-gray-600">{role.description}</p>
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {selectedRole && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <div className="bg-blue-600 text-white p-1 rounded">
                {selectedRole.icon}
              </div>
              <div>
                <h4 className="font-medium text-blue-900">{selectedRole.title}</h4>
                <p className="text-sm text-blue-700">{selectedRole.description}</p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Description (Optional)
          </label>
          <textarea
            value={formData.agentDescription}
            onChange={(e) => handleInputChange('agentDescription', e.target.value)}
            placeholder="Describe what specific tasks this agent should handle..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            rows={3}
          />
        </div>
      </form>
    </div>
  );
};