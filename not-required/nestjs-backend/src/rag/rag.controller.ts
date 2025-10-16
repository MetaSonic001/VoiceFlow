import { Controller, Post, Body } from '@nestjs/common';
import { RagService } from './rag.service';

@Controller('rag')
export class RagController {
  constructor(private readonly ragService: RagService) {}

  @Post('query')
  async query(@Body() body: {
    tenantId: string;
    agentId: string;
    query: string;
    agentConfig: any;
  }) {
    return {
      response: await this.ragService.processQuery(
        body.tenantId,
        body.agentId,
        body.query,
        body.agentConfig
      ),
    };
  }
}