const axios = require('axios');
const Redis = require('ioredis');

class RagService {
  constructor() {
    this.chromaBaseUrl = process.env.CHROMA_URL || 'http://localhost:8002';
    this.groqApiKey = process.env.GROQ_API_KEY || '';
    this.groqBaseUrl = 'https://api.groq.com/openai/v1';
    this.redis = new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: process.env.REDIS_PORT || 6379
    });
  }

  async queryDocuments(tenantId, agentId, query, topK = 5) {
    try {
      const collectionName = `tenant_${tenantId}`;
      const response = await axios.post(`${this.chromaBaseUrl}/api/v1/collections/${collectionName}/query`, {
        query_texts: [query],
        n_results: topK,
        where: { agentId },
      });

      return response.data.results[0]?.documents || [];
    } catch (error) {
      console.error('Error querying Chroma:', error);
      return [];
    }
  }

  async generateResponse(systemPrompt, context, userQuery, tokenLimit = 4096) {
    try {
      // Estimate token count and condense if needed
      const estimatedTokens = this.estimateTokens(systemPrompt + context.join(' ') + userQuery);

      let finalContext = context;
      if (estimatedTokens > tokenLimit * 0.8) { // Leave 20% buffer
        finalContext = await this.condenseContext(context, userQuery, tokenLimit);
      }

      const contextText = finalContext.join('\n\n');
      const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: `Context:\n${contextText}\n\n${userQuery}` },
      ];

      const response = await axios.post(
        `${this.groqBaseUrl}/chat/completions`,
        {
          model: 'grok-beta',
          messages,
          max_tokens: Math.min(1000, Math.floor(tokenLimit * 0.2)), // Reserve tokens for response
          temperature: 0.7,
        },
        {
          headers: {
            'Authorization': `Bearer ${this.groqApiKey}`,
            'Content-Type': 'application/json',
          },
          timeout: 30000, // 30 second timeout
        }
      );

      return response.data.choices[0].message.content;
    } catch (error) {
      console.error('Error generating response:', error);
      throw new Error('Failed to generate response');
    }
  }

  async processQuery(tenantId, agentId, query, agent, sessionId = 'default') {
    try {
      // Get conversation history from Redis
      const conversationKey = `conversation:${tenantId}:${agentId}:${sessionId}`;
      let conversation = [];

      try {
        const conversationData = await this.redis.get(conversationKey);
        if (conversationData) {
          conversation = JSON.parse(conversationData);
        }
      } catch (redisError) {
        console.warn('Redis error getting conversation:', redisError);
      }

      // Query documents
      const contexts = await this.queryDocuments(tenantId, agentId, query);

      // Add current query to conversation
      conversation.push({ role: 'user', content: query });

      // Generate response
      const response = await this.generateResponse(
        agent.systemPrompt || 'You are a helpful assistant.',
        contexts,
        query,
        agent.tokenLimit || 4096
      );

      // Add response to conversation
      conversation.push({ role: 'assistant', content: response });

      // Keep only last 20 messages to prevent context bloat
      if (conversation.length > 20) {
        conversation = conversation.slice(-20);
      }

      // Store updated conversation in Redis with TTL (24 hours)
      try {
        await this.redis.setex(conversationKey, 86400, JSON.stringify(conversation));
      } catch (redisError) {
        console.warn('Redis error storing conversation:', redisError);
      }

      return response;
    } catch (error) {
      console.error('Error processing query:', error);
      throw error;
    }
  }

  estimateTokens(text) {
    // Rough estimation: 1 token ≈ 4 characters for English text
    return Math.ceil(text.length / 4);
  }

  async condenseContext(context, query, maxTokens) {
    try {
      // Simple condensation: keep most relevant chunks
      const queryWords = query.toLowerCase().split(/\s+/);
      const scoredContexts = context.map(chunk => {
        const chunkWords = chunk.toLowerCase().split(/\s+/);
        const score = queryWords.reduce((acc, word) => {
          return acc + (chunkWords.includes(word) ? 1 : 0);
        }, 0);
        return { chunk, score };
      });

      // Sort by relevance and keep top chunks within token limit
      scoredContexts.sort((a, b) => b.score - a.score);

      let condensed = [];
      let totalTokens = 0;

      for (const item of scoredContexts) {
        const tokens = this.estimateTokens(item.chunk);
        if (totalTokens + tokens <= maxTokens * 0.6) { // Use 60% of limit for context
          condensed.push(item.chunk);
          totalTokens += tokens;
        } else {
          break;
        }
      }

      return condensed;
    } catch (error) {
      console.warn('Error condensing context, using original:', error);
      return context.slice(0, 3); // Fallback to first 3 chunks
    }
  }

  async cleanup() {
    if (this.redis) {
      await this.redis.quit();
    }
  }
}

module.exports = new RagService();