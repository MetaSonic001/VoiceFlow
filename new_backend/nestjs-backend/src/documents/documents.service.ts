import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma.service';
import { Document } from '@prisma/client';

@Injectable()
export class DocumentsService {
  constructor(private prisma: PrismaService) {}

  async create(data: {
    agentId: string;
    url?: string;
    s3Path?: string;
    status?: string;
    title?: string;
    content?: string;
    metadata?: any;
  }): Promise<Document> {
    return this.prisma.document.create({
      data,
    });
  }

  async findByAgentId(agentId: string): Promise<Document[]> {
    return this.prisma.document.findMany({
      where: { agentId },
    });
  }

  async findById(id: string): Promise<Document | null> {
    return this.prisma.document.findUnique({
      where: { id },
    });
  }

  async update(id: string, data: {
    status?: string;
    title?: string;
    content?: string;
    metadata?: any;
  }): Promise<Document> {
    return this.prisma.document.update({
      where: { id },
      data,
    });
  }

  async delete(id: string): Promise<Document> {
    return this.prisma.document.delete({
      where: { id },
    });
  }
}