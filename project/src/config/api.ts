// API Configuration
export const apiConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  wsBaseURL: import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
};

// Get auth token from localStorage
const getAuthToken = () => localStorage.getItem('auth_token');

// API Client with all FastAPI routes
export const apiClient = {
  // Authentication Routes
  async signup(email: string, password: string, name: string, company?: string) {
    const response = await fetch(`${apiConfig.baseUrl}/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password, name, company }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Signup failed');
    }
    
    const data = await response.json();
    if (data.access_token) {
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('session_id', data.session_id);
    }
    return data;
  },

  async login(email: string, password: string) {
    const response = await fetch(`${apiConfig.baseUrl}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }
    
    const data = await response.json();
    if (data.access_token) {
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('session_id', data.session_id);
    }
    return data;
  },

  async logout() {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/auth/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    localStorage.removeItem('auth_token');
    localStorage.removeItem('session_id');
    localStorage.removeItem('user');
    
    if (!response.ok) {
      throw new Error('Logout failed');
    }
    
    return response.json();
  },

  async getMe() {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/auth/me`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch user info');
    }
    
    return response.json();
  },

  // Onboarding Routes
  async saveCompanyProfile(data: any) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/onboarding/company`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error('Failed to save company profile');
    }
    
    return response.json();
  },

  async createAgent(data: any) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/onboarding/agent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error('Failed to create agent');
    }
    
    return response.json();
  },

  async uploadKnowledge(formData: FormData) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/onboarding/knowledge`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error('Failed to upload knowledge');
    }
    
    return response.json();
  },

  async saveVoiceConfig(data: any) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/onboarding/voice`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error('Failed to save voice configuration');
    }
    
    return response.json();
  },

  async saveChannelConfig(data: any) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/onboarding/channels`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error('Failed to save channel configuration');
    }
    
    return response.json();
  },

  async deployAgent() {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/onboarding/deploy`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to deploy agent');
    }
    
    return response.json();
  },

  async getOnboardingStatus() {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/onboarding/status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to get onboarding status');
    }
    
    return response.json();
  },

  // Agent Management Routes
  async getAgents() {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/agents`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch agents');
    }
    
    return response.json();
  },

  async getAgent(agentId: string) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/agents/${agentId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch agent');
    }
    
    return response.json();
  },

  async updateAgent(agentId: string, data: any) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/agents/${agentId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error('Failed to update agent');
    }
    
    return response.json();
  },

  async deleteAgent(agentId: string) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/agents/${agentId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to delete agent');
    }
    
    return response.json();
  },

  async toggleAgent(agentId: string) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/agents/${agentId}/pause`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to toggle agent');
    }
    
    return response.json();
  },

  // Conversation Routes
  async sendMessage(sessionId: string, message: string) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/conversations/${sessionId}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    
    return response.json();
  },

  async sendAudio(sessionId: string, audioData: FormData) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/conversations/${sessionId}/audio`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: audioData,
    });
    
    if (!response.ok) {
      throw new Error('Failed to send audio');
    }
    
    return response.json();
  },

  // Analytics Routes
  async getAnalyticsOverview() {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/analytics/overview`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch analytics overview');
    }
    
    return response.json();
  },

  async getAnalyticsMetrics(timeRange?: string) {
    const token = getAuthToken();
    const url = new URL(`${apiConfig.baseUrl}/analytics/metrics`);
    if (timeRange) url.searchParams.append('time_range', timeRange);
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch analytics metrics');
    }
    
    return response.json();
  },

  async getCallLogs(params?: { page?: number; limit?: number; agent_id?: string }) {
    const token = getAuthToken();
    const url = new URL(`${apiConfig.baseUrl}/calls/logs`);
    if (params?.page) url.searchParams.append('page', params.page.toString());
    if (params?.limit) url.searchParams.append('limit', params.limit.toString());
    if (params?.agent_id) url.searchParams.append('agent_id', params.agent_id);
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch call logs');
    }
    
    return response.json();
  },

  async getCallDetails(callId: string) {
    const token = getAuthToken();
    const response = await fetch(`${apiConfig.baseUrl}/calls/${callId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch call details');
    }
    
    return response.json();
  },

  // Utility Routes
  async healthCheck() {
    const response = await fetch(`${apiConfig.baseUrl}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error('Health check failed');
    }
    
    return response.json();
  },

  // Legacy methods for backward compatibility
  async getConversations(params?: any) {
    return this.getCallLogs(params);
  }
};