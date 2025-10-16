const express = require('express');
const router = express.Router();
const Joi = require('joi');

// Validation schemas
const querySchema = Joi.object({
  query: Joi.string().required().min(1).max(1000),
  agentId: Joi.string().required(),
  sessionId: Joi.string().optional()
});

// Middleware to validate tenant access
const validateTenantAccess = (req, res, next) => {
  const tenantId = req.headers['x-tenant-id'] || req.query.tenantId;
  if (!tenantId) {
    return res.status(400).json({ error: 'Tenant ID required' });
  }
  req.tenantId = tenantId;
  next();
};

// Query agent with RAG
router.post('/query', validateTenantAccess, async (req, res) => {
  try {
    const { error, value } = querySchema.validate(req.body);
    if (error) {
      return res.status(400).json({ error: error.details[0].message });
    }

    const prisma = req.app.get('prisma');
    const { query, agentId, sessionId } = value;

    // Verify agent belongs to tenant
    const agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        user: { id: req.tenantId }
      }
    });

    if (!agent) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const ragService = require('../services/ragService');
    const response = await ragService.processQuery(
      req.tenantId,
      agentId,
      query,
      agent,
      sessionId
    );

    res.json({
      response: response,
      agentId: agentId,
      sessionId: sessionId || 'default'
    });
  } catch (error) {
    console.error('Error processing RAG query:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get conversation history
router.get('/conversation/:sessionId', validateTenantAccess, async (req, res) => {
  try {
    const { sessionId } = req.params;
    const { agentId } = req.query;

    if (!agentId) {
      return res.status(400).json({ error: 'Agent ID required' });
    }

    const prisma = req.app.get('prisma');

    // Verify agent belongs to tenant
    const agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        user: { id: req.tenantId }
      }
    });

    if (!agent) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const redis = req.app.get('redis');
    const conversationKey = `conversation:${req.tenantId}:${agentId}:${sessionId}`;
    const conversation = await redis.get(conversationKey);

    res.json({
      sessionId: sessionId,
      conversation: conversation ? JSON.parse(conversation) : []
    });
  } catch (error) {
    console.error('Error fetching conversation:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Clear conversation history
router.delete('/conversation/:sessionId', validateTenantAccess, async (req, res) => {
  try {
    const { sessionId } = req.params;
    const { agentId } = req.query;

    if (!agentId) {
      return res.status(400).json({ error: 'Agent ID required' });
    }

    const prisma = req.app.get('prisma');

    // Verify agent belongs to tenant
    const agent = await prisma.agent.findFirst({
      where: {
        id: agentId,
        user: { id: req.tenantId }
      }
    });

    if (!agent) {
      return res.status(403).json({ error: 'Access denied' });
    }

    const redis = req.app.get('redis');
    const conversationKey = `conversation:${req.tenantId}:${agentId}:${sessionId}`;
    await redis.del(conversationKey);

    res.status(204).send();
  } catch (error) {
    console.error('Error clearing conversation:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;