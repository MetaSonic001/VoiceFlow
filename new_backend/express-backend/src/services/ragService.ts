import axios, { AxiosResponse } from 'axios';
import Redis from 'ioredis';

interface Agent {
  systemPrompt?: string;
  tokenLimit?: number;
}

interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChromaQueryResponse {
  results: {
    documents: string[];
  }[];
}

interface ChromaGetResponse {
  documents: string[];
}

interface GroqResponse {
  choices: Array<{
    message: {
      content: string;
    };
  }>;
}

class RagService {
  private chromaBaseUrl: string;
  private groqApiKey: string;
  private groqBaseUrl: string;
  private redis: Redis;

  constructor() {
    this.chromaBaseUrl = process.env.CHROMA_URL || 'http://localhost:8002';
    this.groqApiKey = process.env.GROQ_API_KEY || '';
    this.groqBaseUrl = 'https://api.groq.com/openai/v1';
    this.redis = new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379', 10)
    });
  }

  async queryDocuments(tenantId: string, agentId: string, query: string, topK: number = 5, maxTokens: number = 4000): Promise<string[]> {
    try {
      const collectionName = `tenant_${tenantId}`;

      // Get semantic search results
      const semanticResults = await this.semanticSearch(collectionName, query, agentId, Math.floor(topK * 0.7));

      // Get keyword search results using BM25
      const keywordResults = await this.keywordSearch(collectionName, query, agentId, Math.floor(topK * 0.3));

      // Combine and deduplicate results
      const combinedResults = [...semanticResults, ...keywordResults];
      const uniqueResults = Array.from(new Set(combinedResults));

      // Re-rank by relevance to query
      const scoredResults = uniqueResults.map(doc => ({
        content: doc,
        score: this.calculateRelevanceScore(doc, query)
      }));

      scoredResults.sort((a, b) => b.score - a.score);

      // Extract top results and condense to fit token limits
      const topResults = scoredResults.slice(0, topK).map(item => item.content);
      const condensedContext = await this.condenseContext(topResults, query, maxTokens);

      console.log(`RAG Query: "${query}" - Retrieved ${topResults.length} chunks, condensed to ${condensedContext.length} (${this.estimateTokens(condensedContext.join(' '))} tokens)`);

      return condensedContext;
    } catch (error) {
      console.error('Error querying documents:', error);
      return []; // Return empty array on error to prevent hallucinations
    }
  }

  private async semanticSearch(collectionName: string, query: string, agentId: string, limit: number): Promise<string[]> {
    try {
      const response: AxiosResponse<ChromaQueryResponse> = await axios.post(`${this.chromaBaseUrl}/api/v1/collections/${collectionName}/query`, {
        query_texts: [query],
        n_results: limit,
        where: { agentId },
      });

      return response.data.results[0]?.documents || [];
    } catch (error) {
      console.warn('Semantic search failed, falling back to empty results:', error);
      return [];
    }
  }

  private async keywordSearch(collectionName: string, query: string, agentId: string, limit: number): Promise<string[]> {
    try {
      // Simple keyword-based search using ChromaDB metadata filtering
      // In production, you might want to implement BM25 indexing here
      const queryWords = query.toLowerCase().split(/\s+/).filter(word => word.length > 2);

      if (queryWords.length === 0) {
        return [];
      }

      // Get more results than needed for BM25-like scoring
      const response: AxiosResponse<ChromaGetResponse> = await axios.post(`${this.chromaBaseUrl}/api/v1/collections/${collectionName}/get`, {
        where: { agentId },
        limit: limit * 3, // Get more for scoring
      });

      const documents = response.data.documents || [];

      // Score documents using BM25-like algorithm
      const scoredDocs = documents.map((doc: string) => ({
        content: doc,
        score: this.calculateBM25Score(doc, queryWords)
      }));

      scoredDocs.sort((a: { content: string; score: number }, b: { content: string; score: number }) => b.score - a.score);

      return scoredDocs.slice(0, limit).map((item: { content: string; score: number }) => item.content);
    } catch (error) {
      console.warn('Keyword search failed:', error);
      return [];
    }
  }

  private calculateBM25Score(document: string, queryWords: string[]): number {
    const docWords = document.toLowerCase().split(/\s+/);
    const docLength = docWords.length;
    const avgDocLength = 100; // Approximate average document length
    const k1 = 1.5; // BM25 parameter
    const b = 0.75; // BM25 parameter

    let score = 0;
    const termFreq = new Map<string, number>();

    // Count term frequencies in document
    for (const word of docWords) {
      termFreq.set(word, (termFreq.get(word) || 0) + 1);
    }

    for (const queryWord of queryWords) {
      const tf = termFreq.get(queryWord) || 0;
      if (tf > 0) {
        // Simplified BM25 scoring (without IDF calculation for performance)
        const numerator = tf * (k1 + 1);
        const denominator = tf + k1 * (1 - b + b * (docLength / avgDocLength));
        score += numerator / denominator;
      }
    }

    return score;
  }

  private calculateRelevanceScore(document: string, query: string): number {
    const queryWords = query.toLowerCase().split(/\s+/);
    const docWords = document.toLowerCase().split(/\s+/);

    let score = 0;

    // Exact phrase matching (highest weight)
    if (document.toLowerCase().includes(query.toLowerCase())) {
      score += 10;
    }

    // Individual word matching
    for (const queryWord of queryWords) {
      if (queryWord.length > 2) { // Skip very short words
        const regex = new RegExp(`\\b${queryWord}\\b`, 'i');
        if (regex.test(document)) {
          score += 1;
        }
      }
    }

    // Proximity bonus (words appearing close together)
    let proximityScore = 0;
    for (let i = 0; i < queryWords.length - 1; i++) {
      const word1 = queryWords[i];
      const word2 = queryWords[i + 1];

      const index1 = docWords.indexOf(word1.toLowerCase());
      const index2 = docWords.indexOf(word2.toLowerCase());

      if (index1 !== -1 && index2 !== -1) {
        const distance = Math.abs(index2 - index1);
        proximityScore += Math.max(0, 5 - distance); // Bonus for close words
      }
    }

    score += proximityScore * 0.5;

    return score;
  }

  async generateResponse(systemPrompt: string, context: string[], userQuery: string, tokenLimit: number = 4096): Promise<string> {
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

      const response: AxiosResponse<GroqResponse> = await axios.post(
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

  async processQuery(tenantId: string, agentId: string, query: string, agent: Agent, sessionId: string = 'default'): Promise<string> {
    try {
      // Get conversation history from Redis
      const conversationKey = `conversation:${tenantId}:${agentId}:${sessionId}`;
      let conversation: ConversationMessage[] = [];

      try {
        const conversationData = await this.redis.get(conversationKey);
        if (conversationData) {
          conversation = JSON.parse(conversationData);
        }
      } catch (redisError) {
        console.warn('Redis error getting conversation:', redisError);
      }

      // Query documents
      const contexts = await this.queryDocuments(tenantId, agentId, query, 10);

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

  private estimateTokens(text: string): number {
    // More accurate token estimation for English text
    // Based on OpenAI's tokenization patterns
    if (!text) return 0;

    // Count words (split on whitespace and punctuation)
    const words = text.split(/[\s\n]+/).filter(word => word.length > 0);

    // Estimate tokens: ~0.75 tokens per word on average for English
    // Add extra for punctuation and subword tokenization
    const wordTokens = words.length * 0.75;

    // Add tokens for punctuation and special characters
    const punctuationCount = (text.match(/[.,!?;:"'()[\]{}]/g) || []).length;
    const punctuationTokens = punctuationCount * 0.3;

    // Add tokens for numbers and symbols
    const numberCount = (text.match(/\d+/g) || []).length;
    const numberTokens = numberCount * 0.5;

    return Math.ceil(wordTokens + punctuationTokens + numberTokens);
  }

  private async condenseContext(context: string[], query: string, maxTokens: number): Promise<string[]> {
    try {
      if (context.length === 0) return [];

      // Calculate available tokens for context (leave room for system prompt and response)
      const availableTokens = Math.floor(maxTokens * 0.5); // Use 50% for context

      // Score and rank contexts by relevance
      const scoredContexts = context.map(chunk => ({
        content: chunk,
        score: this.calculateRelevanceScore(chunk, query),
        tokens: this.estimateTokens(chunk)
      }));

      // Sort by relevance score (descending)
      scoredContexts.sort((a, b) => b.score - a.score);

      // Select top chunks that fit within token limit
      const selectedChunks: string[] = [];
      let totalTokens = 0;

      for (const item of scoredContexts) {
        if (totalTokens + item.tokens <= availableTokens) {
          selectedChunks.push(item.content);
          totalTokens += item.tokens;
        } else if (item.tokens > availableTokens * 0.3) {
          // If a highly relevant chunk is too big, truncate it
          const truncated = this.truncateText(item.content, availableTokens - totalTokens);
          if (truncated) {
            selectedChunks.push(truncated);
            break;
          }
        }
      }

      // Ensure we have at least some context if possible
      if (selectedChunks.length === 0 && context.length > 0) {
        // Take the most relevant chunk and truncate if necessary
        const bestChunk = scoredContexts[0].content;
        const truncated = this.truncateText(bestChunk, availableTokens);
        if (truncated) {
          selectedChunks.push(truncated);
        }
      }

      return selectedChunks;
    } catch (error) {
      console.warn('Error condensing context, using fallback:', error);
      // Fallback: take first chunk and truncate to fit
      const firstChunk = context[0];
      const truncated = this.truncateText(firstChunk, Math.floor(maxTokens * 0.4));
      return truncated ? [truncated] : [];
    }
  }

  private truncateText(text: string, maxTokens: number): string {
    if (this.estimateTokens(text) <= maxTokens) {
      return text;
    }

    // Truncate to approximately maxTokens
    const estimatedChars = maxTokens * 4; // Rough conversion
    let truncated = text.substring(0, estimatedChars);

    // Try to cut at a sentence boundary
    const lastSentenceEnd = Math.max(
      truncated.lastIndexOf('.'),
      truncated.lastIndexOf('!'),
      truncated.lastIndexOf('?'),
      truncated.lastIndexOf('\n')
    );

    if (lastSentenceEnd > estimatedChars * 0.5) {
      truncated = truncated.substring(0, lastSentenceEnd + 1);
    }

    return truncated.trim();
  }

  async cleanup(): Promise<void> {
    if (this.redis) {
      await this.redis.quit();
    }
  }
}

export default new RagService();