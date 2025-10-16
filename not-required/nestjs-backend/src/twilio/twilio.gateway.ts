import { WebSocketGateway, WebSocketServer, SubscribeMessage, MessageBody, ConnectedSocket } from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { RagService } from '../rag/rag.service';
import { AgentsService } from '../agents/agents.service';
import { VoiceService } from '../voice/voice.service';

@WebSocketGateway({ cors: true })
export class TwilioGateway {
  @WebSocketServer()
  server: Server;

  constructor(
    private ragService: RagService,
    private agentsService: AgentsService,
    private voiceService: VoiceService,
  ) {}

  @SubscribeMessage('start')
  async handleStart(
    @MessageBody() data: { tenantId: string; agentId: string; streamSid: string },
    @ConnectedSocket() client: Socket,
  ) {
    console.log('Twilio stream started:', data);
    // Store session info
    client.data = {
      ...data,
      conversation: [],
      audioBuffer: Buffer.alloc(0)
    };
  }

  @SubscribeMessage('media')
  async handleMedia(
    @MessageBody() data: { media: { payload: string } },
    @ConnectedSocket() client: Socket,
  ) {
    try {
      // Decode base64 audio
      const audioChunk = Buffer.from(data.media.payload, 'base64');
      client.data.audioBuffer = Buffer.concat([client.data.audioBuffer, audioChunk]);

      // Process audio when we have enough data (e.g., 1 second of audio at 16kHz)
      if (client.data.audioBuffer.length >= 32000) { // ~1 second
        const transcript = await this.voiceService.transcribeAudio(client.data.audioBuffer);

        if (transcript && transcript.trim()) {
          console.log('Transcript:', transcript);

          const { tenantId, agentId } = client.data;
          const agent = await this.agentsService.findById(agentId);

          if (agent) {
            // Add to conversation history
            client.data.conversation.push({ role: 'user', content: transcript });

            const response = await this.ragService.processQuery(
              tenantId,
              agentId,
              transcript,
              agent,
              client.data.conversation
            );

            // Add assistant response to conversation
            client.data.conversation.push({ role: 'assistant', content: response });

            // Generate speech
            const audioResponse = await this.voiceService.generateSpeech(
              response,
              agent.voiceType || 'female'
            );

            // Send audio response back to Twilio
            const audioBase64 = audioResponse.toString('base64');
            client.emit('response', {
              text: response,
              audio: audioBase64
            });
          }
        }

        // Reset audio buffer
        client.data.audioBuffer = Buffer.alloc(0);
      }
    } catch (error) {
      console.error('Error processing media:', error);
    }
  }

  @SubscribeMessage('stop')
  handleStop(@ConnectedSocket() client: Socket) {
    console.log('Twilio stream stopped');
    // Clean up session data
    if (client.data) {
      client.data = null;
    }
  }
}
  }
}