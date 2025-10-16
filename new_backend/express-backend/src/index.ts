import 'dotenv/config';
import express, { Request, Response, Application } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { createServer, Server as HTTPServer } from 'http';
import { Server as SocketIOServer, Socket } from 'socket.io';
import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';

// Interfaces
interface SocketData {
  tenantId: string;
  agentId: string;
  streamSid: string;
  conversation: Array<{ role: string; content: string }>;
  audioBuffer: Buffer;
}

interface MediaData {
  media: {
    payload: string;
  };
}

interface TwilioResponse {
  text: string;
  audio: string;
}

// Extend Socket interface
declare module 'socket.io' {
  interface Socket {
    data: SocketData;
  }
}

// Initialize Express app
const app: Application = express();
const server: HTTPServer = createServer(app);
const io: SocketIOServer = new SocketIOServer(server, {
  cors: {
    origin: process.env.FRONTEND_URL || "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

// Initialize Prisma
const prisma = new PrismaClient();

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use(limiter);

// Make services available in routes
app.set('prisma', prisma);

// Initialize Redis
const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379')
});
app.set('redis', redis);

// Routes
app.use('/api/agents', require('./routes/agents'));
app.use('/api/documents', require('./routes/documents'));
app.use('/api/rag', require('./routes/rag'));
app.use('/api/ingestion', require('./routes/ingestion'));
app.use('/api/runner', require('./routes/runner'));
app.use('/api/users', require('./routes/users'));

// Health check
app.get('/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Socket.IO for Twilio Media Streams
io.on('connection', (socket: Socket) => {
  console.log('Client connected:', socket.id);

  socket.on('start', async (data: SocketData) => {
    console.log('Twilio stream started:', data);
    socket.data = {
      ...data,
      conversation: [],
      audioBuffer: Buffer.alloc(0)
    };
  });

  socket.on('media', async (data: MediaData) => {
    try {
      const voiceService = require('./services/voiceService');
      const ragService = require('./services/ragService');

      // Decode base64 audio
      const audioChunk = Buffer.from(data.media.payload, 'base64');
      socket.data.audioBuffer = Buffer.concat([socket.data.audioBuffer, audioChunk]);

      // Process audio when we have enough data
      if (socket.data.audioBuffer.length >= 32000) {
        const transcript = await voiceService.transcribeAudio(socket.data.audioBuffer);

        if (transcript && transcript.trim()) {
          console.log('Transcript:', transcript);

          const { tenantId, agentId } = socket.data;
          const agent = await prisma.agent.findFirst({
            where: {
              id: agentId,
              user: { id: tenantId }
            }
          });

          if (agent) {
            socket.data.conversation.push({ role: 'user', content: transcript });

            const response = await ragService.processQuery(
              tenantId,
              agentId,
              transcript,
              agent,
              socket.data.conversation
            );

            socket.data.conversation.push({ role: 'assistant', content: response });

            const audioResponse = await voiceService.generateSpeech(
              response,
              agent.voiceType || 'female'
            );

            const audioBase64 = audioResponse.toString('base64');
            socket.emit('response', {
              text: response,
              audio: audioBase64
            } as TwilioResponse);
          }
        }

        socket.data.audioBuffer = Buffer.alloc(0);
      }
    } catch (error) {
      console.error('Error processing media:', error);
    }
  });

  socket.on('stop', () => {
    console.log('Twilio stream stopped');
    socket.data = null as any;
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

const PORT = process.env.PORT || 8000;

server.listen(PORT, () => {
  console.log(`Express server running on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully');
  await prisma.$disconnect();
  await redis.quit();
  server.close(() => {
    console.log('Process terminated');
  });
});

process.on('SIGINT', async () => {
  console.log('SIGINT received, shutting down gracefully');
  await prisma.$disconnect();
  await redis.quit();
  server.close(() => {
    console.log('Process terminated');
  });
});