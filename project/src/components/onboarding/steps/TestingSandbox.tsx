import React, { useState } from 'react';
import { Play, MessageSquare, Phone, Volume2, Mic, Send, Loader } from 'lucide-react';
import { Button } from '../../ui/Button';
import { apiClient } from '../../../config/api';

interface TestingSandboxProps {
  data: Record<string, any>;
  onDataChange: (data: Record<string, any>) => void;
  onNext: () => void;
}

export const TestingSandbox: React.FC<TestingSandboxProps> = ({ data, onDataChange, onNext }) => {
  const [activeTest, setActiveTest] = useState<'chat' | 'phone' | null>(null);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { type: 'bot', message: `Hi! I'm ${data.agentName || 'your AI agent'}. How can I help you today?` }
  ]);
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const sendChatMessage = async () => {
    if (!chatMessage.trim()) return;
    
    const userMessage = chatMessage;
    setChatMessage('');
    setChatHistory(prev => [...prev, { type: 'user', message: userMessage }]);
    setIsLoading(true);
    
    try {
      const sessionId = localStorage.getItem('session_id');
      if (sessionId) {
        const response = await apiClient.sendMessage(sessionId, userMessage);
        setChatHistory(prev => [...prev, { 
          type: 'bot', 
          message: response.response || 'Thanks for your message! This is a test response from your AI agent.'
        }]);
      } else {
        // Fallback for testing without session
        setTimeout(() => {
          setChatHistory(prev => [...prev, { 
            type: 'bot', 
            message: 'Thanks for your message! This is a test response from your AI agent. In the live version, I would provide helpful information based on your uploaded knowledge base.' 
          }]);
        }, 1000);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setChatHistory(prev => [...prev, { 
        type: 'bot', 
        message: 'I apologize, but I encountered an error. Please try again or contact support if the issue persists.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const startPhoneTest = () => {
    setActiveTest('phone');
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
  };

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Test your AI agent</h2>
        <p className="text-gray-600">Try out your agent before going live</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Chat Testing */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <MessageSquare className="h-5 w-5 mr-2" />
            Chat Testing
          </h3>
          
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
            <div className="bg-blue-600 text-white p-4 rounded-t-xl">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                  <MessageSquare className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-medium">{data.agentName || 'AI Agent'}</div>
                  <div className="text-xs opacity-75">Online</div>
                </div>
              </div>
            </div>
            
            <div className="h-80 overflow-y-auto p-4 space-y-3">
              {chatHistory.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs px-4 py-2 rounded-lg ${
                      msg.type === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    {msg.message}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg flex items-center space-x-2">
                    <Loader className="h-4 w-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                </div>
              )}
            </div>
            
            <div className="p-4 border-t">
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  placeholder="Type your test message..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  onKeyPress={(e) => e.key === 'Enter' && !isLoading && sendChatMessage()}
                  disabled={isLoading}
                />
                <button
                  onClick={sendChatMessage}
                  disabled={isLoading || !chatMessage.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Phone Testing */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <Phone className="h-5 w-5 mr-2" />
            Voice Call Testing
          </h3>
          
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
            <div className="text-center space-y-4">
              <div className={`w-20 h-20 rounded-full mx-auto flex items-center justify-center ${
                activeTest === 'phone' 
                  ? 'bg-green-100 border-4 border-green-500' 
                  : 'bg-gray-100'
              }`}>
                <Phone className={`h-8 w-8 ${
                  activeTest === 'phone' ? 'text-green-600' : 'text-gray-400'
                }`} />
              </div>
              
              <div>
                <h4 className="font-semibold text-gray-900">Test Voice Call</h4>
                <p className="text-sm text-gray-600">
                  {activeTest === 'phone' 
                    ? 'Call simulation active...' 
                    : 'Start a test call with your agent'
                  }
                </p>
              </div>

              {activeTest !== 'phone' ? (
                <Button onClick={startPhoneTest} className="w-full">
                  <Play className="h-4 w-4 mr-2" />
                  Start Test Call
                </Button>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-center space-x-4">
                    <button
                      onClick={toggleRecording}
                      className={`p-4 rounded-full transition-colors ${
                        isRecording 
                          ? 'bg-red-500 text-white animate-pulse' 
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      <Mic className="h-6 w-6" />
                    </button>
                    <button className="p-4 rounded-full bg-gray-100 text-gray-600">
                      <Volume2 className="h-6 w-6" />
                    </button>
                  </div>
                  
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-700">
                      {isRecording 
                        ? "🎤 Listening... Speak now to test your agent"
                        : "Click the microphone to start speaking"
                      }
                    </p>
                  </div>
                  
                  <Button 
                    variant="outline" 
                    onClick={() => setActiveTest(null)}
                    className="w-full"
                  >
                    End Test Call
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Test Summary */}
      <div className="bg-blue-50 rounded-xl p-6 border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Testing Checklist:</h3>
        <div className="grid md:grid-cols-2 gap-4">
          <ul className="space-y-2 text-sm text-gray-700">
            <li>✅ Ask questions about your uploaded documents</li>
            <li>✅ Test the agent's personality and tone</li>
            <li>✅ Try edge cases and unusual requests</li>
          </ul>
          <ul className="space-y-2 text-sm text-gray-700">
            <li>✅ Verify response accuracy and relevance</li>
            <li>✅ Check fallback responses for unknown queries</li>
            <li>✅ Test conversation flow and context retention</li>
          </ul>
        </div>
      </div>

      <div className="flex justify-end pt-6">
        <Button onClick={onNext}>
          Ready to Go Live
        </Button>
      </div>
    </div>
  );
};