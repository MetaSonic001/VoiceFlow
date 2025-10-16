import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios from 'axios';

@Injectable()
export class IngestionService {
  private fastApiUrl: string;

  constructor(private configService: ConfigService) {
    this.fastApiUrl = this.configService.get('FASTAPI_URL', 'http://localhost:8001');
  }

  async startIngestion(tenantId: string, agentId: string, urls: string[], s3Urls: string[]) {
    try {
      const response = await axios.post(`${this.fastApiUrl}/ingest`, {
        tenantId,
        agentId,
        urls,
        s3_urls: s3Urls,
      });
      return response.data;
    } catch (error) {
      throw new Error('Failed to start ingestion');
    }
  }

  async getIngestionStatus(jobId: string) {
    try {
      const response = await axios.get(`${this.fastApiUrl}/status/${jobId}`);
      return response.data;
    } catch (error) {
      throw new Error('Failed to get status');
    }
  }
}