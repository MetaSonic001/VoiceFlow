import React, { useState } from 'react';
import { Building, Globe, Users, Target } from 'lucide-react';
import { Input } from '../../ui/Input';

const industries = [
  'Technology', 'Healthcare', 'Finance', 'E-commerce', 'Education',
  'Real Estate', 'Automotive', 'Manufacturing', 'Consulting', 'Other'
];

const companySizes = [
  '1-10 employees', '11-50 employees', '51-200 employees',
  '201-1000 employees', '1000+ employees'
];

const useCases = [
  'Customer Support', 'Sales & Lead Qualification', 'HR & Employee Queries',
  'Appointment Scheduling', 'Order Management', 'Technical Support'
];

interface CompanySetupProps {
  data: Record<string, any>;
  onDataChange: (data: Record<string, any>) => void;
  onNext: () => void;
}

export const CompanySetup: React.FC<CompanySetupProps> = ({ data, onDataChange, onNext }) => {
  const [formData, setFormData] = useState({
    companyName: data.companyName || '',
    website: data.website || '',
    industry: data.industry || '',
    companySize: data.companySize || '',
    primaryUseCase: data.primaryUseCase || '',
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

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Tell us about your company</h2>
        <p className="text-gray-600">This helps us customize your AI agent experience</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid md:grid-cols-2 gap-6">
          <Input
            label="Company Name"
            type="text"
            value={formData.companyName}
            onChange={(e) => handleInputChange('companyName', e.target.value)}
            placeholder="Acme Corporation"
            icon={<Building className="h-5 w-5" />}
            required
          />

          <Input
            label="Website (Optional)"
            type="url"
            value={formData.website}
            onChange={(e) => handleInputChange('website', e.target.value)}
            placeholder="https://acmecorp.com"
            icon={<Globe className="h-5 w-5" />}
          />
        </div>

        <div className="space-y-4">
          <label className="block text-sm font-medium text-gray-700">Industry</label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {industries.map(industry => (
              <label
                key={industry}
                className={`flex items-center p-3 rounded-lg border-2 cursor-pointer transition-all ${
                  formData.industry === industry
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="industry"
                  value={industry}
                  checked={formData.industry === industry}
                  onChange={(e) => handleInputChange('industry', e.target.value)}
                  className="sr-only"
                />
                <span className="text-sm font-medium text-gray-900">{industry}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <label className="block text-sm font-medium text-gray-700">
            <Users className="h-4 w-4 inline mr-2" />
            Company Size
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {companySizes.map(size => (
              <label
                key={size}
                className={`flex items-center p-3 rounded-lg border-2 cursor-pointer transition-all ${
                  formData.companySize === size
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="companySize"
                  value={size}
                  checked={formData.companySize === size}
                  onChange={(e) => handleInputChange('companySize', e.target.value)}
                  className="sr-only"
                />
                <span className="text-sm font-medium text-gray-900">{size}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <label className="block text-sm font-medium text-gray-700">
            <Target className="h-4 w-4 inline mr-2" />
            Primary Use Case
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {useCases.map(useCase => (
              <label
                key={useCase}
                className={`flex items-center p-3 rounded-lg border-2 cursor-pointer transition-all ${
                  formData.primaryUseCase === useCase
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="primaryUseCase"
                  value={useCase}
                  checked={formData.primaryUseCase === useCase}
                  onChange={(e) => handleInputChange('primaryUseCase', e.target.value)}
                  className="sr-only"
                />
                <span className="text-sm font-medium text-gray-900">{useCase}</span>
              </label>
            ))}
          </div>
        </div>
      </form>
    </div>
  );
};