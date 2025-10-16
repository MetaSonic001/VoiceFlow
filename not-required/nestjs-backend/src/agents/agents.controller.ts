import { Controller, Get, Post, Put, Delete, Param, Body, Query, Headers } from '@nestjs/common';
import { AgentsService } from './agents.service';

@Controller('agents')
export class AgentsController {
  constructor(private readonly agentsService: AgentsService) {}

  @Post()
  async createAgent(@Body() body: {
    name: string;
    userId: string;
    systemPrompt?: string;
    voiceType?: string;
    llmPreferences?: any;
    tokenLimit?: number;
    contextWindowStrategy?: string;
  }) {
    return this.agentsService.create(body);
  }

  @Get()
  async getAgents(
    @Query('userId') userId: string,
    @Query('page') page: number = 1,
    @Query('limit') limit: number = 20,
    @Query('search') search: string = '',
    @Query('status') status: string = '',
  ) {
    const agents = await this.agentsService.findByUserId(userId);
    // Apply pagination and filtering
    let filtered = agents;
    if (search) {
      filtered = filtered.filter(a => a.name.toLowerCase().includes(search.toLowerCase()));
    }
    const start = (page - 1) * limit;
    const paginated = filtered.slice(start, start + limit);

    return {
      agents: paginated,
      total: filtered.length,
      page,
      limit,
    };
  }

  @Get(':id')
  async getAgent(@Param('id') id: string) {
    return this.agentsService.findById(id);
  }

  @Put(':id')
  async updateAgent(@Param('id') id: string, @Body() body: {
    name?: string;
    systemPrompt?: string;
    voiceType?: string;
    llmPreferences?: any;
    tokenLimit?: number;
    contextWindowStrategy?: string;
  }) {
    return this.agentsService.update(id, body);
  }

  @Delete(':id')
  async deleteAgent(@Param('id') id: string) {
    return this.agentsService.delete(id);
  }
}