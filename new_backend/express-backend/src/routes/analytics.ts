import express, { Request, Response, NextFunction, Router } from 'express';

const router: Router = express.Router();

// Extend Request interface
declare global {
  namespace Express {
    interface Request {
      tenantId: string;
      userId: string;
    }
  }
}

// Get analytics overview metrics
router.get('/overview', async (req: Request, res: Response) => {
  try {
    const { timeRange = '7d', agentId } = req.query;

    // Mock analytics data - in production, this would query the database
    const overviewData = {
      totalInteractions: 12847,
      successRate: 94.2,
      avgResponseTime: 2.1,
      customerSatisfaction: 4.7,
      totalCalls: 8234,
      totalChats: 4613,
      activeCalls: 8,
      activeChats: 12,
      queuedInteractions: 3,
      topIssues: [
        { issue: "Password Reset", count: 234, percentage: 18.2 },
        { issue: "Billing Questions", count: 189, percentage: 14.7 },
        { issue: "Product Information", count: 156, percentage: 12.1 },
        { issue: "Technical Support", count: 134, percentage: 10.4 },
        { issue: "Account Setup", count: 98, percentage: 7.6 },
      ],
      channelPerformance: {
        phone: { count: 8234, avgDuration: "4m 32s", successRate: 96 },
        chat: { count: 4613, avgDuration: "2m 18s", successRate: 92 },
        whatsapp: { count: 1456, avgDuration: "3m 45s", successRate: 89 },
      }
    };

    res.json(overviewData);
  } catch (error) {
    console.error('Error fetching analytics overview:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get call logs
router.get('/calls', async (req: Request, res: Response) => {
  try {
    const { page = 1, limit = 50, search, status, type, agentId } = req.query;

    // Mock call logs data - in production, this would query the database
    const mockCallLogs = [
      {
        id: "call-001",
        type: "phone",
        customerInfo: "+1 (555) 987-6543",
        agentName: "Customer Support Assistant",
        agentId: "agent-1",
        startTime: "2024-01-15T14:30:25Z",
        duration: 204, // seconds
        status: "completed",
        resolution: "resolved",
        summary: "Customer inquiry about product pricing and availability. Provided detailed information about current promotions.",
        sentiment: "positive",
        tags: ["pricing", "product-info"],
        transcript: "Customer: Hi, I need information about your pricing...",
      },
      {
        id: "call-002",
        type: "chat",
        customerInfo: "Anonymous User",
        agentName: "Customer Support Assistant",
        agentId: "agent-1",
        startTime: "2024-01-15T14:25:12Z",
        duration: 105,
        status: "completed",
        resolution: "resolved",
        summary: "Password reset assistance. Guided customer through the reset process successfully.",
        sentiment: "neutral",
        tags: ["password-reset", "account"],
        transcript: "Customer: I forgot my password...",
      },
      {
        id: "call-003",
        type: "phone",
        customerInfo: "+1 (555) 123-9876",
        agentName: "Sales Qualifier",
        agentId: "agent-2",
        startTime: "2024-01-15T14:20:08Z",
        duration: 312,
        status: "escalated",
        resolution: "escalated",
        summary: "Complex billing issue requiring human intervention. Customer had multiple questions about charges.",
        sentiment: "negative",
        tags: ["billing", "escalation"],
        transcript: "Customer: I'm confused about my bill...",
      },
    ];

    // Apply filters
    let filteredLogs = mockCallLogs;

    if (search) {
      const searchTerm = search.toString().toLowerCase();
      filteredLogs = filteredLogs.filter(log =>
        log.customerInfo.toLowerCase().includes(searchTerm) ||
        log.summary.toLowerCase().includes(searchTerm) ||
        log.tags.some(tag => tag.toLowerCase().includes(searchTerm))
      );
    }

    if (status && status !== 'all') {
      filteredLogs = filteredLogs.filter(log => log.status === status);
    }

    if (type && type !== 'all') {
      filteredLogs = filteredLogs.filter(log => log.type === type);
    }

    if (agentId && agentId !== 'all') {
      filteredLogs = filteredLogs.filter(log => log.agentId === agentId);
    }

    // Pagination
    const startIndex = (parseInt(page.toString()) - 1) * parseInt(limit.toString());
    const endIndex = startIndex + parseInt(limit.toString());
    const paginatedLogs = filteredLogs.slice(startIndex, endIndex);

    res.json({
      logs: paginatedLogs,
      total: filteredLogs.length,
      page: parseInt(page.toString()),
      limit: parseInt(limit.toString()),
      totalPages: Math.ceil(filteredLogs.length / parseInt(limit.toString())),
    });
  } catch (error) {
    console.error('Error fetching call logs:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get realtime metrics
router.get('/realtime', async (req: Request, res: Response) => {
  try {
    // Mock realtime data - in production, this would use WebSocket or polling
    const realtimeData = {
      activeCalls: Math.floor(Math.random() * 15) + 5,
      activeChats: Math.floor(Math.random() * 20) + 10,
      avgResponseTime: Math.round((Math.random() * 2 + 1.5) * 10) / 10,
      successRate: Math.round((Math.random() * 10 + 85) * 10) / 10,
      queuedInteractions: Math.floor(Math.random() * 10),
      timestamp: new Date().toISOString(),
    };

    res.json(realtimeData);
  } catch (error) {
    console.error('Error fetching realtime metrics:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get metrics chart data
router.get('/metrics-chart', async (req: Request, res: Response) => {
  try {
    const { timeRange = '7d', agentId } = req.query;

    // Generate mock chart data
    const chartData = [];
    const now = new Date();
    const days = timeRange === '24h' ? 24 : timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);

      chartData.push({
        date: date.toISOString().split('T')[0],
        calls: Math.floor(Math.random() * 100) + 50,
        chats: Math.floor(Math.random() * 150) + 75,
        total: 0, // Will be calculated below
        successRate: Math.round((Math.random() * 10 + 85) * 10) / 10,
        avgResponseTime: Math.round((Math.random() * 2 + 1.5) * 10) / 10,
      });
    }

    // Calculate totals
    chartData.forEach(day => {
      day.total = day.calls + day.chats;
    });

    res.json({ data: chartData });
  } catch (error) {
    console.error('Error fetching metrics chart data:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get agent comparison data
router.get('/agent-comparison', async (req: Request, res: Response) => {
  try {
    const { timeRange = '7d' } = req.query;

    // Mock agent comparison data
    const comparisonData = [
      {
        agentId: 'agent-1',
        agentName: 'Customer Support Assistant',
        totalInteractions: 5421,
        successRate: 96.2,
        avgResponseTime: 1.8,
        customerSatisfaction: 4.8,
      },
      {
        agentId: 'agent-2',
        agentName: 'Sales Qualifier',
        totalInteractions: 2134,
        successRate: 89.7,
        avgResponseTime: 2.2,
        customerSatisfaction: 4.5,
      },
      {
        agentId: 'agent-3',
        agentName: 'HR Assistant',
        totalInteractions: 987,
        successRate: 94.1,
        avgResponseTime: 2.5,
        customerSatisfaction: 4.6,
      },
    ];

    res.json({ agents: comparisonData });
  } catch (error) {
    console.error('Error fetching agent comparison data:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;