import React, { useState, useEffect } from 'react';
import { X, Mail, Lock, User, Building } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  mode: 'login' | 'signup';
}

// Mock Button component
const Button: React.FC<{
  type?: 'button' | 'submit';
  className?: string;
  loading?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}> = ({ type = 'button', className = '', loading = false, children, onClick }) => (
  <button
    type={type}
    className={`px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 ${
      className.includes('w-full') ? 'w-full' : ''
    } bg-blue-600 hover:bg-blue-700 text-white ${className}`}
    disabled={loading}
    onClick={onClick}
  >
    {loading ? (
      <div className="flex items-center justify-center">
        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading...
      </div>
    ) : (
      children
    )}
  </button>
);

// Mock Input component
const Input: React.FC<{
  label: string;
  type: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder: string;
  icon: React.ReactNode;
  error?: string;
  required?: boolean;
}> = ({ label, type, value, onChange, placeholder, icon, error, required }) => (
  <div className="space-y-2">
    <label className="block text-sm font-medium text-gray-700">{label}</label>
    <div className="relative">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
        {icon}
      </div>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        className={`block w-full pl-10 pr-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
          error ? 'border-red-300' : 'border-gray-300'
        }`}
      />
    </div>
    {error && <p className="text-red-600 text-sm">{error}</p>}
  </div>
);

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, mode: initialMode }) => {
  const [mode, setMode] = useState(initialMode);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    company: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const { login, signup, user } = useAuth();

  // Reset form when modal opens/closes or mode changes
  useEffect(() => {
    if (!isOpen) {
      setFormData({
        email: '',
        password: '',
        name: '',
        company: ''
      });
      setErrors({});
    }
  }, [isOpen]);

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  // Close modal when user becomes authenticated
  useEffect(() => {
    if (user && isOpen) {
      onClose();
    }
  }, [user, isOpen, onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrors({});

    try {
      if (mode === 'login') {
        await login(formData.email, formData.password);
      } else {
        await signup(formData.email, formData.password, formData.name, formData.company);
      }
      // Don't call onClose() here - let the useEffect handle it when user state updates
    } catch (error: any) {
      setErrors({ general: error.message || 'An error occurred' });
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleModeSwitch = () => {
    const newMode = mode === 'login' ? 'signup' : 'login';
    setMode(newMode);
    setErrors({});
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md transform transition-all">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'login' ? 'Welcome back' : 'Get started'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {errors.general && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-red-600 text-sm">{errors.general}</p>
              </div>
            )}

            {mode === 'signup' && (
              <>
                <Input
                  label="Full Name"
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="John Doe"
                  icon={<User className="h-5 w-5" />}
                  error={errors.name}
                  required
                />
                <Input
                  label="Company Name"
                  type="text"
                  value={formData.company}
                  onChange={(e) => handleInputChange('company', e.target.value)}
                  placeholder="Acme Corporation"
                  icon={<Building className="h-5 w-5" />}
                  error={errors.company}
                />
              </>
            )}

            <Input
              label="Email Address"
              type="email"
              value={formData.email}
              onChange={(e) => handleInputChange('email', e.target.value)}
              placeholder="john@company.com"
              icon={<Mail className="h-5 w-5" />}
              error={errors.email}
              required
            />

            <Input
              label="Password"
              type="password"
              value={formData.password}
              onChange={(e) => handleInputChange('password', e.target.value)}
              placeholder="••••••••"
              icon={<Lock className="h-5 w-5" />}
              error={errors.password}
              required
            />

            <Button type="submit" className="w-full" loading={loading}>
              {mode === 'login' ? 'Sign In' : 'Create Account'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-gray-600">
              {mode === 'login' ? "Don't have an account? " : "Already have an account? "}
              <button
                type="button"
                onClick={handleModeSwitch}
                className="text-blue-600 hover:text-blue-700 font-medium"
                disabled={loading}
              >
                {mode === 'login' ? 'Sign up' : 'Sign in'}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};