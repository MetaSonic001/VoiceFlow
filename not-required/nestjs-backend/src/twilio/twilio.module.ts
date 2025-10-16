import { Module } from '@nestjs/common';
import { TwilioGateway } from './twilio.gateway';
import { RagModule } from '../rag/rag.module';
import { AgentsModule } from '../agents/agents.module';

@Module({
  imports: [RagModule, AgentsModule],
  providers: [TwilioGateway],
})
export class TwilioModule {}