import { Twilio } from 'twilio';
import * as vosk from 'vosk';
import { Readable } from 'stream';
import RagService from './ragService';
import VoiceService from './voiceService';

export interface TwilioMediaConfig {
  accountSid: string;
  authToken: string;
  phoneNumber: string;
  voskModelPath: string;
}

export class TwilioMediaService {
  private twilioClient: Twilio;
  private voskModel: vosk.Model;
  private ragService: typeof RagService;
  private voiceService: typeof VoiceService;
  private activeStreams: Map<string, vosk.Recognizer> = new Map();

  constructor(
    config: TwilioMediaConfig,
    ragService: typeof RagService,
    voiceService: typeof VoiceService
  ) {
    this.twilioClient = new Twilio(config.accountSid, config.authToken);
    this.ragService = ragService;
    this.voiceService = voiceService;

    // Initialize Vosk model
    vosk.setLogLevel(-1); // Disable logging
    this.voskModel = new vosk.Model(config.voskModelPath);
  }

  /**
   * Generate TwiML for handling voice calls
   */
  generateVoiceResponse(): string {
    const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://${process.env.NGROK_URL || 'localhost:3000'}/media-stream" />
  </Connect>
</Response>`;
    return twiml;
  }

  /**
   * Process incoming audio frame from Twilio stream
   */
  async processAudioFrame(callSid: string, audioData: Buffer): Promise<string | null> {
    try {
      // Get or create recognizer for this call
      let recognizer = this.activeStreams.get(callSid);
      if (!recognizer) {
        recognizer = new vosk.Recognizer({ model: this.voskModel, sampleRate: 16000 });
        this.activeStreams.set(callSid, recognizer);
      }

      // Process audio data
      const isFinal = recognizer.acceptWaveform(audioData);
      let transcription = '';

      if (isFinal) {
        const result = recognizer.result();
        transcription = result.text;
      } else {
        const partial = recognizer.partialResult();
        transcription = partial.partial;
      }

      // If we have a complete transcription, process it with RAG
      if (isFinal && transcription.trim()) {
        const response = await this.processWithRAG(transcription, callSid);
        return response;
      }

      return null; // No response yet
    } catch (error) {
      console.error('Error processing audio frame:', error);
      return 'I apologize, but I encountered an error processing your request.';
    }
  }

  /**
   * Transcribe audio using VoiceService (placeholder implementation)
   */
  private async transcribeAudio(audioData: Buffer): Promise<string> {
    // This is a placeholder - in production, you'd integrate with VoiceService
    // For now, we'll return a mock transcription for testing
    console.log(`Processing ${audioData.length} bytes of audio data`);

    // Mock transcription - replace with actual VoiceService integration
    return "Hello, how can I help you today?";
  }

  /**
   * Process transcription with RAG system
   */
  private async processWithRAG(transcription: string, callSid: string): Promise<string> {
    try {
      // For voice calls, we'll use default tenant and agent IDs
      // In production, these should be determined based on the call context
      const tenantId = 'default';
      const agentId = 'voice-agent';
      const agent = {
        systemPrompt: 'You are a helpful AI assistant providing information through voice calls. Keep your responses clear and concise for voice communication.',
        tokenLimit: 1000
      };

      const response = await this.ragService.processQuery(tenantId, agentId, transcription, agent, callSid);
      return response;
    } catch (error) {
      console.error('Error processing with RAG:', error);
      return 'I apologize, but I encountered an error processing your question.';
    }
  }

  /**
   * Generate TTS audio from text response using VoiceService
   */
  async generateTTSResponse(text: string): Promise<Buffer> {
    try {
      // Use the existing VoiceService for TTS (Coqui TTS - open source and free)
      const audioBuffer = await this.voiceService.generateSpeech(text, 'female');
      return audioBuffer;
    } catch (error) {
      console.error('Error generating TTS:', error);
      // Fallback to a simple beep if TTS fails
      return this.generateFallbackAudio(text);
    }
  }

  /**
   * Process complete audio file for web interface (not streaming)
   */
  async processAudioForWeb(audioBuffer: Buffer, agentId: string, sessionId: string): Promise<{ transcript: string; response: string }> {
    try {
      // Transcribe the complete audio
      const transcript = await this.transcribeCompleteAudio(audioBuffer);

      if (!transcript.trim()) {
        return {
          transcript: '',
          response: 'I apologize, but I couldn\'t understand the audio. Please try speaking more clearly.'
        };
      }

      // Process with RAG
      const response = await this.processWithRAGForWeb(transcript, agentId, sessionId);

      return {
        transcript,
        response
      };
    } catch (error) {
      console.error('Error processing audio for web:', error);
      return {
        transcript: '',
        response: 'I apologize, but I encountered an error processing your audio.'
      };
    }
  }

  /**
   * Transcribe complete audio buffer using Vosk
   * Note: Currently expects raw PCM audio. Frontend sends WebM which needs conversion.
   */
  private async transcribeCompleteAudio(audioBuffer: Buffer): Promise<string> {
    try {
      // TODO: Add audio format conversion from WebM to PCM
      // For now, this will likely fail with WebM format
      console.log(`Processing audio buffer of ${audioBuffer.length} bytes`);

      // Create a temporary recognizer for this audio
      const recognizer = new vosk.Recognizer({ model: this.voskModel, sampleRate: 16000 });

      // Convert Buffer to Int16Array for Vosk
      const audioData = new Int16Array(audioBuffer.buffer, audioBuffer.byteOffset, audioBuffer.length / 2);

      // Process the entire audio buffer
      recognizer.acceptWaveform(audioData);

      // Get the final result
      const result = recognizer.result();
      const transcript = result.text;

      console.log(`Transcription result: "${transcript}"`);

      // Clean up
      recognizer.free();

      return transcript;
    } catch (error) {
      console.error('Error transcribing audio:', error);
      return '';
    }
  }

  /**
   * Process transcription with RAG for web interface
   */
  private async processWithRAGForWeb(transcription: string, agentId: string, sessionId: string): Promise<string> {
    try {
      // Use default tenant for web interface
      const tenantId = 'default';

      // Get agent info (you might want to fetch this from database)
      const agent = {
        systemPrompt: 'You are a helpful AI assistant. Provide clear, accurate, and concise responses.',
        tokenLimit: 2000
      };

      const response = await this.ragService.processQuery(tenantId, agentId, transcription, agent, sessionId);
      return response;
    } catch (error) {
      console.error('Error processing with RAG for web:', error);
      return 'I apologize, but I encountered an error processing your question.';
    }
  }

  /**
   * Clean up resources for a call
   */
  cleanupCall(callSid: string): void {
    this.activeStreams.delete(callSid);
  }

  /**
   * Make an outbound call
   */
  async makeOutboundCall(to: string): Promise<string> {
    try {
      const call = await this.twilioClient.calls.create({
        to: to,
        from: process.env.TWILIO_PHONE_NUMBER!,
        twiml: this.generateVoiceResponse(),
      });

      return call.sid;
    } catch (error) {
      console.error('Error making outbound call:', error);
      throw new Error('Failed to initiate outbound call');
    }
  }

  /**
   * Get call status
   */
  async getCallStatus(callSid: string): Promise<any> {
    try {
      const call = await this.twilioClient.calls(callSid).fetch();
      return {
        sid: call.sid,
        status: call.status,
        duration: call.duration,
        direction: call.direction,
      };
    } catch (error) {
      console.error('Error fetching call status:', error);
      throw new Error('Failed to get call status');
    }
  }
}