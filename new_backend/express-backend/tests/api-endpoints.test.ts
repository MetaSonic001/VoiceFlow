import request from 'supertest';
import express from 'express';
import analyticsRouter from '../src/routes/analytics';
import adminRouter from '../src/routes/admin';
import agentsRouter from '../src/routes/agents';
import authRouter from '../src/routes/auth';
import documentsRouter from '../src/routes/documents';
import onboardingRouter from '../src/routes/onboarding';
import ragRouter from '../src/routes/rag';
import ingestionRouter from '../src/routes/ingestion';
import runnerRouter from '../src/routes/runner';
import twilioRouter from '../src/routes/twilio';
import usersRouter from '../src/routes/users';

// Mock middleware
jest.mock('../src/middleware/clerkAuth', () => ({
  createClerkAuth: () => (req: any, res: any, next: any) => {
    req.tenantId = 'test-tenant';
    req.userId = 'test-user';
    next();
  }
}));

jest.mock('../src/middleware/rateLimit', () => ({
  createTenantRateLimit: () => (req: any, res: any, next: any) => next()
}));

describe('Analytics API Endpoints', () => {
  let app: express.Application;

  beforeAll(() => {
    app = express();
    app.use(express.json());

    // Mock Redis for rate limiting
    const mockRedis = {
      get: jest.fn(),
      set: jest.fn(),
      incr: jest.fn(),
      expire: jest.fn()
    };
    app.set('redis', mockRedis);

    // Mount routes
    app.use('/analytics', analyticsRouter);
    app.use('/admin', adminRouter);
    app.use('/api/agents', agentsRouter);
    app.use('/auth', authRouter);
    app.use('/api/documents', documentsRouter);
    app.use('/onboarding', onboardingRouter);
    app.use('/api/rag', ragRouter);
    app.use('/api/ingestion', ingestionRouter);
    app.use('/api/runner', runnerRouter);
    app.use('/twilio', twilioRouter);
    app.use('/users', usersRouter);
  });

  describe('GET /analytics/overview', () => {
    it('should return analytics overview data', async () => {
      const response = await request(app)
        .get('/analytics/overview')
        .query({ timeRange: '7d' });

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('totalInteractions');
      expect(response.body).toHaveProperty('successRate');
      expect(response.body).toHaveProperty('avgResponseTime');
      expect(response.body).toHaveProperty('customerSatisfaction');
      expect(response.body).toHaveProperty('topIssues');
      expect(response.body).toHaveProperty('channelPerformance');
    });

    it('should handle different time ranges', async () => {
      const response = await request(app)
        .get('/analytics/overview')
        .query({ timeRange: '30d' });

      expect(response.status).toBe(200);
    });
  });

  describe('GET /analytics/calls', () => {
    it('should return call logs with pagination', async () => {
      const response = await request(app)
        .get('/analytics/calls')
        .query({ page: 1, limit: 10 });

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('calls');
      expect(response.body).toHaveProperty('total');
      expect(response.body).toHaveProperty('page');
      expect(response.body).toHaveProperty('limit');
    });

    it('should support filtering by status', async () => {
      const response = await request(app)
        .get('/analytics/calls')
        .query({ status: 'completed', page: 1, limit: 5 });

      expect(response.status).toBe(200);
      expect(Array.isArray(response.body.calls)).toBe(true);
    });

    it('should support search functionality', async () => {
      const response = await request(app)
        .get('/analytics/calls')
        .query({ search: 'test', page: 1, limit: 5 });

      expect(response.status).toBe(200);
    });
  });

  describe('GET /analytics/realtime', () => {
    it('should return real-time metrics', async () => {
      const response = await request(app)
        .get('/analytics/realtime');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('active_calls');
      expect(response.body).toHaveProperty('active_chats');
      expect(response.body).toHaveProperty('queued_interactions');
      expect(response.body).toHaveProperty('online_agents');
    });
  });

  describe('GET /analytics/metrics-chart', () => {
    it('should return chart data for metrics', async () => {
      const response = await request(app)
        .get('/analytics/metrics-chart')
        .query({ timeRange: '7d' });

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('labels');
      expect(response.body).toHaveProperty('datasets');
      expect(Array.isArray(response.body.labels)).toBe(true);
      expect(Array.isArray(response.body.datasets)).toBe(true);
    });
  });

  describe('GET /analytics/agent-comparison', () => {
    it('should return agent comparison data', async () => {
      const response = await request(app)
        .get('/analytics/agent-comparison');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('agents');
      expect(Array.isArray(response.body.agents)).toBe(true);
    });
  });

  describe('Admin Pipeline Endpoints', () => {
    describe('GET /admin/pipeline_agents', () => {
      it('should return pipeline agents', async () => {
        const response = await request(app)
          .get('/admin/pipeline_agents');

        expect(response.status).toBe(200);
        expect(Array.isArray(response.body)).toBe(true);
      });
    });

    describe('POST /admin/pipelines', () => {
      it('should create a new pipeline', async () => {
        const pipelineData = {
          name: 'Test Pipeline',
          description: 'A test pipeline',
          agentIds: ['agent-1', 'agent-2'],
          config: { steps: [] }
        };

        const response = await request(app)
          .post('/admin/pipelines')
          .send(pipelineData);

        expect(response.status).toBe(201);
        expect(response.body).toHaveProperty('id');
        expect(response.body.name).toBe(pipelineData.name);
      });
    });

    describe('POST /admin/pipelines/trigger', () => {
      it('should trigger a pipeline execution', async () => {
        const triggerData = {
          pipelineId: 'test-pipeline-id',
          input: { message: 'Test input' }
        };

        const response = await request(app)
          .post('/admin/pipelines/trigger')
          .send(triggerData);

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('executionId');
        expect(response.body).toHaveProperty('status');
      });
    });
  });

  describe('Agent Management Endpoints', () => {
    describe('GET /api/agents', () => {
      it('should return agents list', async () => {
        const response = await request(app)
          .get('/api/agents')
          .query({ page: 1, limit: 10 });

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('agents');
        expect(response.body).toHaveProperty('total');
      });
    });

    describe('POST /api/agents', () => {
      it('should create a new agent', async () => {
        const agentData = {
          name: 'Test Agent',
          description: 'A test agent',
          type: 'chatbot',
          config: {
            model: 'gpt-4',
            temperature: 0.7
          }
        };

        const response = await request(app)
          .post('/api/agents')
          .send(agentData);

        expect(response.status).toBe(201);
        expect(response.body).toHaveProperty('id');
        expect(response.body.name).toBe(agentData.name);
      });
    });
  });

  describe('Onboarding Endpoints', () => {
    describe('GET /onboarding/progress', () => {
      it('should return onboarding progress', async () => {
        const response = await request(app)
          .get('/onboarding/progress');

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('exists');
      });
    });

    describe('POST /onboarding/progress', () => {
      it('should update onboarding progress', async () => {
        const progressData = {
          step: 'company-setup',
          completed: true,
          data: { companyName: 'Test Corp' }
        };

        const response = await request(app)
          .post('/onboarding/progress')
          .send(progressData);

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('success');
      });
    });
  });

  describe('Document Management Endpoints', () => {
    describe('POST /api/documents/upload', () => {
      it('should upload a document', async () => {
        const formData = new FormData();
        formData.append('file', new Blob(['test content']), 'test.txt');
        formData.append('metadata', JSON.stringify({ title: 'Test Document' }));

        const response = await request(app)
          .post('/api/documents/upload')
          .set('Content-Type', 'multipart/form-data')
          .send(formData);

        expect(response.status).toBe(201);
        expect(response.body).toHaveProperty('documentId');
      });
    });
  });

  describe('RAG Endpoints', () => {
    describe('POST /api/rag/query', () => {
      it('should process a RAG query', async () => {
        const queryData = {
          query: 'What is machine learning?',
          context: 'AI and ML context',
          filters: { category: 'technical' }
        };

        const response = await request(app)
          .post('/api/rag/query')
          .send(queryData);

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('answer');
        expect(response.body).toHaveProperty('sources');
      });
    });
  });

  describe('Ingestion Endpoints', () => {
    describe('POST /api/ingestion/start', () => {
      it('should start document ingestion', async () => {
        const ingestionData = {
          documentId: 'doc-123',
          options: {
            chunkSize: 1000,
            overlap: 200
          }
        };

        const response = await request(app)
          .post('/api/ingestion/start')
          .send(ingestionData);

        expect(response.status).toBe(202);
        expect(response.body).toHaveProperty('jobId');
        expect(response.body).toHaveProperty('status');
      });
    });
  });

  describe('Runner Endpoints', () => {
    describe('POST /api/runner/execute', () => {
      it('should execute an agent', async () => {
        const executionData = {
          agentId: 'agent-123',
          input: { message: 'Hello, how can I help you?' },
          context: {}
        };

        const response = await request(app)
          .post('/api/runner/execute')
          .send(executionData);

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('response');
        expect(response.body).toHaveProperty('conversationId');
      });
    });
  });

  describe('Twilio Integration Endpoints', () => {
    describe('POST /twilio/webhook', () => {
      it('should handle Twilio webhook', async () => {
        const twilioData = {
          From: '+1234567890',
          Body: 'Hello',
          MessageSid: 'msg-123'
        };

        const response = await request(app)
          .post('/twilio/webhook')
          .send(twilioData);

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('response');
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid JSON', async () => {
      const response = await request(app)
        .post('/analytics/overview')
        .set('Content-Type', 'application/json')
        .send('invalid json');

      expect(response.status).toBe(400);
    });

    it('should handle non-existent endpoints', async () => {
      const response = await request(app)
        .get('/non-existent-endpoint');

      expect(response.status).toBe(404);
    });
  });

  describe('Rate Limiting', () => {
    it('should handle rate limited requests', async () => {
      // This would require mocking the rate limiter to return 429
      // For now, just test that the middleware is applied
      const response = await request(app)
        .get('/analytics/overview');

      expect(response.status).toBe(200);
    });
  });
});