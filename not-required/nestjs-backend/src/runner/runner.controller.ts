import { Controller, Post, Body, All, Req } from '@nestjs/common';
import { RagService } from '../rag/rag.service';
import { AgentsService } from '../agents/agents.service';

@Controller('runner')
export class RunnerController {
  constructor(
    private ragService: RagService,
    private agentsService: AgentsService,
  ) {}

  @Post('chat')
  async chat(@Body() body: {
    tenantId: string;
    agentId: string;
    message: string;
  }) {
    const agent = await this.agentsService.findById(body.agentId);
    if (!agent) {
      throw new Error('Agent not found');
    }

    const response = await this.ragService.processQuery(
      body.tenantId,
      body.agentId,
      body.message,
      agent
    );

    return {
      response,
      agentId: body.agentId,
    };
  }

  // Handle other runner endpoints if needed
  @All('*')
  async proxy(@Req() req: any) {
    // For other endpoints, return not found
    return { error: 'Endpoint not found' };
  }
}