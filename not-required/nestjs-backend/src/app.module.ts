import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { PrismaService } from './prisma.service';
import { UsersModule } from './users/users.module';
import { AgentsModule } from './agents/agents.module';
import { DocumentsModule } from './documents/documents.module';
import { RagModule } from './rag/rag.module';
import { TwilioModule } from './twilio/twilio.module';
import { RunnerModule } from './runner/runner.module';
import { IngestionModule } from './ingestion/ingestion.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
    }),
    UsersModule,
    AgentsModule,
    DocumentsModule,
    RagModule,
    TwilioModule,
    RunnerModule,
    IngestionModule,
  ],
  controllers: [AppController],
  providers: [AppService, PrismaService],
})
export class AppModule {}
