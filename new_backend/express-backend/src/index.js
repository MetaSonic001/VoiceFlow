require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { createServer } = require('http');
const { Server } = require('socket.io');
const { PrismaClient } = require('@prisma/client');

const app = express();
const server = createServer(app);
const io = new Server(server, {
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
const Redis = require('ioredis');
const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379
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
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Socket.IO for Twilio Media Streams
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('start', async (data) => {
    console.log('Twilio stream started:', data);
    socket.data = {
      ...data,
      conversation: [],
      audioBuffer: Buffer.alloc(0)
    };
  });

  socket.on('media', async (data) => {
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
            });
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
    socket.data = null;
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