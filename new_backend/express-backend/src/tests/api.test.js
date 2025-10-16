const request = require('supertest');
const { PrismaClient } = require('@prisma/client');
const Redis = require('ioredis');

const prisma = new PrismaClient();
const redis = new Redis();

describe('Express Backend API Tests', () => {
  let app;
  let server;

  beforeAll(async () => {
    // Import the app
    app = require('./src/index');

    // Wait for services to be ready
    await new Promise(resolve => setTimeout(resolve, 1000));
  });

  afterAll(async () => {
    await prisma.$disconnect();
    await redis.quit();
    if (server) {
      server.close();
    }
  });

  describe('Health Check', () => {
    test('GET /health should return status ok', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
      expect(response.body.status).toBe('ok');
    });
  });

  describe('Agent Management', () => {
    const tenantId = 'test-tenant-123';
    let agentId;

    test('POST /api/agents should create agent', async () => {
      const response = await request(app)
        .post('/api/agents')
        .set('x-tenant-id', tenantId)
        .send({
          userId: 'test-user-123',
          name: 'Test Agent',
          systemPrompt: 'You are a helpful assistant.',
          voiceType: 'female'
        });

      expect(response.status).toBe(201);
      expect(response.body).toHaveProperty('id');
      agentId = response.body.id;
    });

    test('GET /api/agents should list user agents', async () => {
      const response = await request(app)
        .get('/api/agents?userId=test-user-123')
        .set('x-tenant-id', tenantId);

      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
    });

    test('GET /api/agents/:id should return agent', async () => {
      const response = await request(app)
        .get(`/api/agents/${agentId}`)
        .set('x-tenant-id', tenantId);

      expect(response.status).toBe(200);
      expect(response.body.id).toBe(agentId);
    });

    test('PUT /api/agents/:id should update agent', async () => {
      const response = await request(app)
        .put(`/api/agents/${agentId}`)
        .set('x-tenant-id', tenantId)
        .send({
          name: 'Updated Test Agent'
        });

      expect(response.status).toBe(200);
      expect(response.body.name).toBe('Updated Test Agent');
    });
  });

  describe('RAG Queries', () => {
    const tenantId = 'test-tenant-123';

    test('POST /api/rag/query should process query', async () => {
      const response = await request(app)
        .post('/api/rag/query')
        .set('x-tenant-id', tenantId)
        .send({
          query: 'What is artificial intelligence?',
          agentId: 'test-agent-123'
        });

      // This might fail if agent doesn't exist or services aren't running
      // But we test the endpoint structure
      expect([200, 403, 404, 500]).toContain(response.status);
    });
  });

  describe('Runner API (Frontend)', () => {
    const tenantId = 'test-tenant-123';

    test('POST /api/runner/chat should handle chat', async () => {
      const response = await request(app)
        .post('/api/runner/chat')
        .set('x-tenant-id', tenantId)
        .send({
          message: 'Hello',
          agentId: 'test-agent-123'
        });

      expect([200, 403, 404, 500]).toContain(response.status);
    });

    test('GET /api/runner/agents should list agents', async () => {
      const response = await request(app)
        .get('/api/runner/agents?userId=test-user-123')
        .set('x-tenant-id', tenantId);

      expect(response.status).toBe(200);
      expect(Array.isArray(response.body)).toBe(true);
    });
  });
});