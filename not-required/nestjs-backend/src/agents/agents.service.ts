import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma.service';
import { Agent } from '@prisma/client';

@Injectable()
export class AgentsService {
  constructor(private prisma: PrismaService) {}

  async create(data: {
    name: string;
    userId: string;
    systemPrompt?: string;
    voiceType?: string;
    llmPreferences?: any;
    tokenLimit?: number;
    contextWindowStrategy?: string;
  }): Promise<Agent> {
    return this.prisma.agent.create({
      data,
    });
  }

  async findByUserId(userId: string): Promise<Agent[]> {
    return this.prisma.agent.findMany({
      where: { userId },
      include: { documents: true },
    });
  }

  async findById(id: string): Promise<Agent | null> {
    return this.prisma.agent.findUnique({
      where: { id },
      include: { documents: true, user: true },
    });
  }

  async update(id: string, data: {
    name?: string;
    systemPrompt?: string;
    voiceType?: string;
    llmPreferences?: any;
    tokenLimit?: number;
    contextWindowStrategy?: string;
  }): Promise<Agent> {
    return this.prisma.agent.update({
      where: { id },
      data,
    });
  }

  async delete(id: string): Promise<Agent> {
    return this.prisma.agent.delete({
      where: { id },
    });
  }
}