import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios from 'axios';

@Injectable()
export class RagService {
  private chromaBaseUrl: string;
  private groqApiKey: string;
  private groqBaseUrl: string;

  constructor(private configService: ConfigService) {
    this.chromaBaseUrl = this.configService.get('CHROMA_URL', 'http://localhost:8000');
    this.groqApiKey = this.configService.get('GROQ_API_KEY') || '';
    this.groqBaseUrl = 'https://api.groq.com/openai/v1';
  }

  async queryDocuments(tenantId: string, agentId: string, query: string, topK: number = 5): Promise<any[]> {
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

  async generateResponse(systemPrompt: string, context: string[], userQuery: string, tokenLimit: number = 4096): Promise<string> {
    try {
      const contextText = context.join('\n\n');
      const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: `Context:\n${contextText}\n\n${userQuery}` },
      ];

      const response = await axios.post(
        `${this.groqBaseUrl}/chat/completions`,
        {
          model: 'grok-beta',
          messages,
          max_tokens: 1000,
          temperature: 0.7,
        },
        {
          headers: {
            'Authorization': `Bearer ${this.groqApiKey}`,
            'Content-Type': 'application/json',
          },
        }
      );

      return response.data.choices[0].message.content;
    } catch (error) {
      console.error('Error generating response:', error);
      throw new Error('Failed to generate response');
    }
  }

  async processQuery(tenantId: string, agentId: string, query: string, agentConfig: any): Promise<string> {
    // Query documents
    const contexts = await this.queryDocuments(tenantId, agentId, query);

    // Generate response
    const response = await this.generateResponse(
      agentConfig.systemPrompt || 'You are a helpful assistant.',
      contexts,
      query,
      agentConfig.tokenLimit || 4096
    );

    return response;
  }
}