import { Controller, Get, Post, Put, Delete, Param, Body, Query } from '@nestjs/common';
import { DocumentsService } from './documents.service';

@Controller('documents')
export class DocumentsController {
  constructor(private readonly documentsService: DocumentsService) {}

  @Post()
  async createDocument(@Body() body: {
    agentId: string;
    url?: string;
    s3Path?: string;
    status?: string;
    title?: string;
    content?: string;
    metadata?: any;
  }) {
    return this.documentsService.create(body);
  }

  @Get()
  async getDocumentsByAgent(@Query('agentId') agentId: string) {
    return this.documentsService.findByAgentId(agentId);
  }

  @Get(':id')
  async getDocument(@Param('id') id: string) {
    return this.documentsService.findById(id);
  }

  @Put(':id')
  async updateDocument(@Param('id') id: string, @Body() body: {
    status?: string;
    title?: string;
    content?: string;
    metadata?: any;
  }) {
    return this.documentsService.update(id, body);
  }

  @Delete(':id')
  async deleteDocument(@Param('id') id: string) {
    return this.documentsService.delete(id);
  }
}