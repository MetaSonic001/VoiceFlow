import React, { useState, useRef, useEffect } from 'react';
import { 
  BarChart3, 
  Phone, 
  MessageSquare, 
  Users, 
  TrendingUp, 
  Plus,
  Settings,
  Play,
  Pause,
  MoreVertical,
  PhoneCall,
  MessageCircle,
  Activity,
  Eye,
  LogOut,
  User as UserIcon
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Agent } from '../../types';
import { LiveConversations } from './LiveConversations';
import { AnalyticsOverview } from './AnalyticsOverview';
import { useAuth } from '../../context/AuthContext';

const mockAgents: Agent[] = [
  {
    id: '1',
    name: 'Sarah',
    role: 'Customer Support',
    status: 'active',
    channels: [
      { type: 'phone', enabled: true },
      { type: 'chat', enabled: true }
    ],
    personality: {
      tone: 'friendly',
      style: 'Professional and approachable',
      guidelines: ['Always be helpful', 'Use customer name when possible']
    },
    voice: {
      provider: 'ElevenLabs',
      voiceId: 'sarah_v1',
      speed: 1.0,
      stability: 0.8
    },
    createdAt: '2024-01-15',
    totalCalls: 1247,
    successRate: 94.2
  },
  {
    id: '2',
    name: 'Alex',
    role: 'Sales Assistant',
    status: 'paused',
    channels: [
      { type: 'phone', enabled: true }
    ],
    personality: {
      tone: 'sales-driven',
      style: 'Persuasive and enthusiastic',
      guidelines: ['Focus on benefits', 'Ask qualifying questions']
    },
    voice: {
      provider: 'ElevenLabs',
      voiceId: 'alex_v1',
      speed: 1.1,
      stability: 0.7
    },
    createdAt: '2024-01-10',
    totalCalls: 623,
    successRate: 87.5
  }
];

interface DashboardProps {
  onCreateAgent: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onCreateAgent }) => {
  const [agents, setAgents] = useState(mockAgents);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'agents' | 'conversations' | 'analytics'>('overview');
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  
  const { user, logout } = useAuth();

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      // The App.tsx will automatically redirect to home page since user will be null
    } catch (error) {
      console.error('Logout error:', error);
      // Even if logout fails, we'll still be redirected due to local storage being cleared
    }
  };

  const toggleAgentStatus = (agentId: string) => {
    setAgents(prev => prev.map(agent => 
      agent.id === agentId 
        ? { ...agent, status: agent.status === 'active' ? 'paused' : 'active' as 'active' | 'paused' }
        : agent
    ));
  };

  const totalCalls = agents.reduce((sum, agent) => sum + agent.totalCalls, 0);
  const avgSuccessRate = agents.reduce((sum, agent) => sum + agent.successRate, 0) / agents.length;
  const activeAgents = agents.filter(agent => agent.status === 'active').length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            
            <div className="flex items-center space-x-4">
              <Button onClick={onCreateAgent}>
                <Plus className="h-4 w-4 mr-2" />
                Create New Agent
              </Button>
              
              {/* User Menu */}
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                    <UserIcon className="h-4 w-4 text-white" />
                  </div>
                  <span className="text-sm font-medium text-gray-700">
                    {user?.name || user?.email || 'User'}
                  </span>
                </button>
                
                {/* Dropdown Menu */}
                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50">
                    <div className="py-1">
                      <div className="px-4 py-2 text-sm text-gray-700 border-b border-gray-100">
                        <div className="font-medium">{user?.name || 'User'}</div>
                        <div className="text-gray-500">{user?.email}</div>
                        {user?.company && (
                          <div className="text-gray-500">{user.company}</div>
                        )}
                      </div>
                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          // Add settings functionality here if needed
                        }}
                        className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                      >
                        <Settings className="h-4 w-4 mr-2" />
                        Settings
                      </button>
                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          handleLogout();
                        }}
                        className="flex items-center w-full px-4 py-2 text-sm text-red-700 hover:bg-red-50"
                      >
                        <LogOut className="h-4 w-4 mr-2" />
                        Logout
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Navigation Tabs */}
          <div className="flex space-x-8 -mb-px">
            {[
              { id: 'overview', label: 'Overview', icon: <BarChart3 className="h-4 w-4" /> },
              { id: 'agents', label: 'Agents', icon: <Users className="h-4 w-4" /> },
              { id: 'conversations', label: 'Live Conversations', icon: <MessageSquare className="h-4 w-4" /> },
              { id: 'analytics', label: 'Analytics', icon: <Activity className="h-4 w-4" /> }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <div className="flex items-center space-x-3">
                  <div className="bg-blue-100 p-3 rounded-lg">
                    <Users className="h-6 w-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Active Agents</p>
                    <p className="text-2xl font-bold text-gray-900">{activeAgents}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border p-6">
                <div className="flex items-center space-x-3">
                  <div className="bg-green-100 p-3 rounded-lg">
                    <PhoneCall className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Total Calls</p>
                    <p className="text-2xl font-bold text-gray-900">{totalCalls.toLocaleString()}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border p-6">
                <div className="flex items-center space-x-3">
                  <div className="bg-emerald-100 p-3 rounded-lg">
                    <TrendingUp className="h-6 w-6 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Success Rate</p>
                    <p className="text-2xl font-bold text-gray-900">{avgSuccessRate.toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border p-6">
                <div className="flex items-center space-x-3">
                  <div className="bg-purple-100 p-3 rounded-lg">
                    <BarChart3 className="h-6 w-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">This Month</p>
                    <p className="text-2xl font-bold text-gray-900">+23%</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Analytics */}
            <AnalyticsOverview />
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="bg-white rounded-xl shadow-sm border">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Your AI Agents</h2>
            </div>
            
            <div className="divide-y divide-gray-200">
              {agents.map(agent => (
                <div key={agent.id} className="p-6 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="flex-shrink-0">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                          agent.status === 'active' 
                            ? 'bg-green-100 text-green-600' 
                            : 'bg-gray-100 text-gray-400'
                        }`}>
                          <Users className="h-6 w-6" />
                        </div>
                      </div>
                      
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">{agent.name}</h3>
                        <p className="text-sm text-gray-600">{agent.role}</p>
                        
                        <div className="flex items-center space-x-4 mt-2">
                          <div className="flex items-center space-x-1">
                            {agent.channels.map(channel => (
                              <div key={channel.type} className="flex items-center">
                                {channel.type === 'phone' ? (
                                  <Phone className="h-4 w-4 text-gray-400" />
                                ) : (
                                  <MessageCircle className="h-4 w-4 text-gray-400" />
                                )}
                              </div>
                            ))}
                          </div>
                          
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            agent.status === 'active'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {agent.status}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-6">
                      <div className="text-center">
                        <div className="text-lg font-semibold text-gray-900">{agent.totalCalls}</div>
                        <div className="text-xs text-gray-500">Total Calls</div>
                      </div>
                      
                      <div className="text-center">
                        <div className="text-lg font-semibold text-gray-900">{agent.successRate}%</div>
                        <div className="text-xs text-gray-500">Success Rate</div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => toggleAgentStatus(agent.id)}
                          className={`p-2 rounded-lg transition-colors ${
                            agent.status === 'active'
                              ? 'text-red-600 hover:bg-red-50'
                              : 'text-green-600 hover:bg-green-50'
                          }`}
                        >
                          {agent.status === 'active' ? (
                            <Pause className="h-4 w-4" />
                          ) : (
                            <Play className="h-4 w-4" />
                          )}
                        </button>
                        
                        <button className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                          <Settings className="h-4 w-4" />
                        </button>
                        
                        <button className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
                          <Eye className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {agents.length === 0 && (
              <div className="p-12 text-center">
                <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No agents yet</h3>
                <p className="text-gray-600 mb-6">Create your first AI agent to get started</p>
                <Button onClick={onCreateAgent}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Agent
                </Button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'conversations' && <LiveConversations />}
        
        {activeTab === 'analytics' && <AnalyticsOverview />}
      </div>
    </div>
  );
};