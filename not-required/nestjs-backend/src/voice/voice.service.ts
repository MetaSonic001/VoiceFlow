import { Injectable, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as vosk from 'vosk';
import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';

@Injectable()
export class VoiceService implements OnModuleInit {
  private model: vosk.Model;
  private asrEngine: string;
  private ttsEngine: string;
  private coquiPath: string;

  constructor(private configService: ConfigService) {
    this.asrEngine = this.configService.get('ASR_ENGINE', 'vosk');
    this.ttsEngine = this.configService.get('TTS_ENGINE', 'coqui');
    this.coquiPath = this.configService.get('COQUI_PATH', 'tts');
  }

  async onModuleInit() {
    if (this.asrEngine === 'vosk') {
      // Initialize Vosk model
      const modelPath = path.join(process.cwd(), 'models', 'vosk-model');
      if (fs.existsSync(modelPath)) {
        this.model = new vosk.Model(modelPath);
      } else {
        console.warn('Vosk model not found. Please download and place in models/vosk-model/');
      }
    }
  }

  async transcribeAudio(audioBuffer: Buffer, sampleRate: number = 16000): Promise<string> {
    if (this.asrEngine === 'vosk' && this.model) {
      const rec = new vosk.Recognizer({ model: this.model, sampleRate });
      rec.acceptWaveform(audioBuffer);
      const result = rec.result();
      rec.free();
      return result.text || '';
    }

    // Fallback to placeholder
    console.log(`Received ${audioBuffer.length} bytes of audio data`);
    return 'Hello, how can I help you?'; // Placeholder
  }

  async generateSpeech(text: string, voiceType: string = 'female', language: string = 'en'): Promise<Buffer> {
    if (this.ttsEngine === 'coqui') {
      return this.generateCoquiSpeech(text, voiceType, language);
    }

    // Fallback placeholder
    return Buffer.from('placeholder_audio_data');
  }

  private async generateCoquiSpeech(text: string, voiceType: string, language: string): Promise<Buffer> {
    return new Promise((resolve, reject) => {
      const tts = spawn(this.coquiPath, [
        '--text', text,
        '--model_name', `tts_models/${language}/${voiceType}`,
        '--out_path', '-'
      ]);

      const chunks: Buffer[] = [];

      tts.stdout.on('data', (chunk) => {
        chunks.push(chunk);
      });

      tts.on('close', (code) => {
        if (code === 0) {
          resolve(Buffer.concat(chunks));
        } else {
          reject(new Error(`TTS process exited with code ${code}`));
        }
      });

      tts.on('error', (error) => {
        reject(error);
      });
    });
  }

  // Convert audio formats if needed
  convertAudioFormat(audioBuffer: Buffer, fromFormat: string, toFormat: string): Buffer {
    // Placeholder for audio format conversion
    // In production, you might use ffmpeg or similar
    return audioBuffer;
  }
}