import swaggerJSDoc from 'swagger-jsdoc';
import swaggerUi from 'swagger-ui-express';

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'VoiceFlow Multi-Tenant RAG API',
      version: '1.0.0',
      description: 'API for multi-tenant RAG (Retrieval-Augmented Generation) system with voice capabilities',
    },
    servers: [
      {
        url: 'http://localhost:8000',
        description: 'Development server',
      },
      {
        url: 'https://api.voiceflow.com',
        description: 'Production server',
      },
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
        },
        tenantAuth: {
          type: 'apiKey',
          in: 'header',
          name: 'x-tenant-id',
          description: 'Tenant identifier for multi-tenant operations',
        },
      },
      schemas: {
        Error: {
          type: 'object',
          properties: {
            success: {
              type: 'boolean',
              example: false,
            },
            error: {
              type: 'object',
              properties: {
                message: {
                  type: 'string',
                  example: 'Error message',
                },
                code: {
                  type: 'string',
                  example: 'ERROR_CODE',
                },
                timestamp: {
                  type: 'string',
                  format: 'date-time',
                },
              },
            },
          },
        },
        Tenant: {
          type: 'object',
          properties: {
            id: { type: 'string', example: 'tenant-123' },
            name: { type: 'string', example: 'Acme Corp' },
            domain: { type: 'string', example: 'acme.com' },
            apiKey: { type: 'string', example: 'sk-...' },
            isActive: { type: 'boolean', example: true },
            createdAt: { type: 'string', format: 'date-time' },
            updatedAt: { type: 'string', format: 'date-time' },
          },
        },
        User: {
          type: 'object',
          properties: {
            id: { type: 'string', example: 'user-123' },
            email: { type: 'string', format: 'email', example: 'user@acme.com' },
            name: { type: 'string', example: 'John Doe' },
            tenantId: { type: 'string', example: 'tenant-123' },
            createdAt: { type: 'string', format: 'date-time' },
            updatedAt: { type: 'string', format: 'date-time' },
          },
        },
        Agent: {
          type: 'object',
          properties: {
            id: { type: 'string', example: 'agent-123' },
            name: { type: 'string', example: 'Customer Support Agent' },
            systemPrompt: { type: 'string', example: 'You are a helpful customer support agent...' },
            voiceType: { type: 'string', enum: ['male', 'female'], example: 'female' },
            llmPreferences: {
              type: 'object',
              properties: {
                provider: { type: 'string', example: 'groq' },
                model: { type: 'string', example: 'llama-3.1-70b' },
              },
            },
            tokenLimit: { type: 'integer', example: 4096 },
            contextWindowStrategy: { type: 'string', enum: ['sliding', 'summarize'], example: 'sliding' },
            tenantId: { type: 'string', example: 'tenant-123' },
            createdAt: { type: 'string', format: 'date-time' },
            updatedAt: { type: 'string', format: 'date-time' },
          },
        },
        Document: {
          type: 'object',
          properties: {
            id: { type: 'string', example: 'doc-123' },
            url: { type: 'string', format: 'uri', example: 'https://example.com/document.pdf' },
            s3Path: { type: 'string', example: 'tenant-123/1234567890-document.pdf' },
            status: { type: 'string', enum: ['pending', 'processing', 'completed', 'failed'], example: 'completed' },
            content: { type: 'string', example: 'Document content...' },
            metadata: { type: 'object' },
            agentId: { type: 'string', example: 'agent-123' },
            tenantId: { type: 'string', example: 'tenant-123' },
            createdAt: { type: 'string', format: 'date-time' },
            updatedAt: { type: 'string', format: 'date-time' },
          },
        },
      },
    },
    security: [
      {
        bearerAuth: [],
        tenantAuth: [],
      },
    ],
  },
  apis: ['./src/routes/*.ts'], // Path to the API routes
};

const specs = swaggerJSDoc(options);

export { swaggerUi, specs };