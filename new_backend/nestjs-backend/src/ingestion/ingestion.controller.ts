import { Controller, Post, Get, Body, Param } from '@nestjs/common';
import { IngestionService } from './ingestion.service';

@Controller('ingestion')
export class IngestionController {
  constructor(private readonly ingestionService: IngestionService) {}

  @Post('start')
  async startIngestion(@Body() body: {
    tenantId: string;
    agentId: string;
    urls?: string[];
    s3Urls?: string[];
  }) {
    return this.ingestionService.startIngestion(
      body.tenantId,
      body.agentId,
      body.urls || [],
      body.s3Urls || []
    );
  }

  @Get('status/:jobId')
  async getStatus(@Param('jobId') jobId: string) {
    return this.ingestionService.getIngestionStatus(jobId);
  }
}