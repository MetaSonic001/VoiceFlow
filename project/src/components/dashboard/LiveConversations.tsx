import React, { useState, useEffect } from 'react';
import { MessageSquare, Phone, User, Clock, TrendingUp, AlertCircle } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { apiClient } from '../../config/api';

interface Conversation {
  id: string;
  agentId: string;
  agentName: string;
  channel: 'phone' | 'chat' | 'whatsapp';
  status: 'active' | 'completed' | 'escalated';
  startTime: string;
  duration: number;
  customerInfo?: {
    name?: string;
    phone?: string;
    email?: string;
  };
  messages: Array<{
    id: string;
    type: 'user' | 'agent';
    content: string;
    timestamp: string;
    confidence?: number;
  }>;
  sentiment: 'positive' | 'neutral' | 'negative';
  intent: string;
}

export const LiveConversations: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'active' | 'escalated'>('all');

  const { isConnected, lastMessage } = useWebSocket('/ws/conversations', true);

  useEffect(() => {
    // Load initial conversations
    loadConversations();
  }, []);

  useEffect(() => {
    if (lastMessage) {
      handleWebSocketMessage(lastMessage);
    }
  }, [lastMessage]);

  const loadConversations = async () => {
    try {
      const data = await apiClient.getConversations({ status: 'active' });
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'conversation_started':
        setConversations(prev => [message.data, ...prev]);
        break;
      case 'conversation_updated':
        setConversations(prev => 
          prev.map(conv => 
            conv.id === message.data.id ? { ...conv, ...message.data } : conv
          )
        );
        break;
      case 'message_received':
        setConversations(prev =>
          prev.map(conv =>
            conv.id === message.data.conversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, message.data.message]
                }
              : conv
          )
        );
        break;
      case 'conversation_ended':
        setConversations(prev =>
          prev.map(conv =>
            conv.id === message.data.id
              ? { ...conv, status: 'completed' }
              : conv
          )
        );
        break;
    }
  };

  const filteredConversations = conversations.filter(conv => {
    if (filter === 'all') return true;
    if (filter === 'active') return conv.status === 'active';
    if (filter === 'escalated') return conv.status === 'escalated';
    return true;
  });

  const selectedConv = conversations.find(c => c.id === selectedConversation);

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'phone': return <Phone className="h-4 w-4" />;
      case 'chat': return <MessageSquare className="h-4 w-4" />;
      case 'whatsapp': return <MessageSquare className="h-4 w-4" />;
      default: return <MessageSquare className="h-4 w-4" />;
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600 bg-green-100';
      case 'negative': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-100';
      case 'escalated': return 'text-orange-600 bg-orange-100';
      case 'completed': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h2 className="text-lg font-semibold text-gray-900">Live Conversations</h2>
            <div className={`flex items-center space-x-2 px-2 py-1 rounded-full text-xs ${
              isConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
          </div>
          
          <div className="flex space-x-2">
            {['all', 'active', 'escalated'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f as any)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  filter === f
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 divide-x divide-gray-200">
        {/* Conversations List */}
        <div className="max-h-96 overflow-y-auto">
          {filteredConversations.length === 0 ? (
            <div className="p-8 text-center">
              <MessageSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No conversations found</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {filteredConversations.map(conversation => (
                <div
                  key={conversation.id}
                  onClick={() => setSelectedConversation(conversation.id)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                    selectedConversation === conversation.id ? 'bg-blue-50 border-r-2 border-blue-500' : ''
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      {getChannelIcon(conversation.channel)}
                      <span className="font-medium text-gray-900">{conversation.agentName}</span>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(conversation.status)}`}>
                      {conversation.status}
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-4 text-sm text-gray-600 mb-2">
                    <div className="flex items-center space-x-1">
                      <Clock className="h-3 w-3" />
                      <span>{Math.floor(conversation.duration / 60)}m {conversation.duration % 60}s</span>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs ${getSentimentColor(conversation.sentiment)}`}>
                      {conversation.sentiment}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-700 truncate">
                    Intent: {conversation.intent}
                  </p>
                  
                  {conversation.customerInfo?.name && (
                    <p className="text-xs text-gray-500 mt-1">
                      Customer: {conversation.customerInfo.name}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Conversation Details */}
        <div className="max-h-96 overflow-y-auto">
          {selectedConv ? (
            <div className="p-4">
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-gray-900">Conversation Details</h3>
                  {selectedConv.status === 'escalated' && (
                    <div className="flex items-center space-x-1 text-orange-600">
                      <AlertCircle className="h-4 w-4" />
                      <span className="text-sm">Escalated</span>
                    </div>
                  )}
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Agent:</span>
                    <p className="font-medium">{selectedConv.agentName}</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Channel:</span>
                    <p className="font-medium capitalize">{selectedConv.channel}</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Duration:</span>
                    <p className="font-medium">{Math.floor(selectedConv.duration / 60)}m {selectedConv.duration % 60}s</p>
                  </div>
                  <div>
                    <span className="text-gray-600">Sentiment:</span>
                    <p className={`font-medium capitalize ${getSentimentColor(selectedConv.sentiment).split(' ')[0]}`}>
                      {selectedConv.sentiment}
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="font-medium text-gray-900">Messages</h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {selectedConv.messages.map(message => (
                    <div
                      key={message.id}
                      className={`p-3 rounded-lg ${
                        message.type === 'user'
                          ? 'bg-gray-100 ml-4'
                          : 'bg-blue-100 mr-4'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-gray-600">
                          {message.type === 'user' ? 'Customer' : 'Agent'}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-900">{message.content}</p>
                      {message.confidence && (
                        <div className="mt-1">
                          <span className="text-xs text-gray-500">
                            Confidence: {(message.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center">
              <User className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">Select a conversation to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};