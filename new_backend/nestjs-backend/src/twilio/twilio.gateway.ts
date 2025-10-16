import { WebSocketGateway, WebSocketServer, SubscribeMessage, MessageBody, ConnectedSocket } from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { RagService } from '../rag/rag.service';
import { AgentsService } from '../agents/agents.service';

@WebSocketGateway({ cors: true })
export class TwilioGateway {
  @WebSocketServer()
  server: Server;

  constructor(
    private ragService: RagService,
    private agentsService: AgentsService,
  ) {}

  @SubscribeMessage('start')
  async handleStart(
    @MessageBody() data: { tenantId: string; agentId: string; streamSid: string },
    @ConnectedSocket() client: Socket,
  ) {
    console.log('Twilio stream started:', data);
    // Store session info
    client.data = { ...data, conversation: [] };
  }

  @SubscribeMessage('media')
  async handleMedia(
    @MessageBody() data: { media: { payload: string } },
    @ConnectedSocket() client: Socket,
  ) {
    // This would integrate with ASR (Vosk/Whisper)
    // For now, simulate text input
    const text = 'Hello, how can I help you?'; // Placeholder

    if (client.data) {
      const { tenantId, agentId } = client.data;
      const agent = await this.agentsService.findById(agentId);

      if (agent) {
        const response = await this.ragService.processQuery(tenantId, agentId, text, agent);

        // Send response back to Twilio
        client.emit('response', { text: response });
      }
    }
  }

  @SubscribeMessage('stop')
  handleStop(@ConnectedSocket() client: Socket) {
    console.log('Twilio stream stopped');
  }
}