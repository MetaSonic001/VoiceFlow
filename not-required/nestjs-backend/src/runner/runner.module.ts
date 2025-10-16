import { Module } from '@nestjs/common';
import { RunnerController } from './runner.controller';
import { RagModule } from '../rag/rag.module';
import { AgentsModule } from '../agents/agents.module';

@Module({
  controllers: [RunnerController],
  imports: [RagModule, AgentsModule],
})
export class RunnerModule {}