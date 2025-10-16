import vosk from 'vosk';
import * as wav from 'node-wav';
import * as fs from 'fs';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

interface AudioBuffer {
  length: number;
  readInt16LE(offset: number): number;
  writeInt16LE(value: number, offset: number): void;
}

class VoiceService {
  private asrEngine: string;
  private ttsEngine: string;
  private voskModel?: vosk.Model;
  private voskRecognizer?: vosk.Recognizer;

  constructor() {
    this.asrEngine = process.env.ASR_ENGINE || 'vosk'; // vosk or whisper
    this.ttsEngine = process.env.TTS_ENGINE || 'coqui'; // coqui or mozilla

    // Initialize Vosk model if using Vosk
    if (this.asrEngine === 'vosk') {
      const modelPath = process.env.VOSK_MODEL_PATH || path.join(__dirname, '../../models/vosk-model');
      if (fs.existsSync(modelPath)) {
        this.voskModel = new vosk.Model(modelPath);
        this.voskRecognizer = new vosk.Recognizer({ model: this.voskModel, sampleRate: 16000 });
      } else {
        console.warn('Vosk model not found, ASR will not work');
      }
    }
  }

  async transcribeAudio(audioBuffer: Buffer): Promise<string> {
    try {
      if (this.asrEngine === 'vosk' && this.voskRecognizer) {
        // Convert audio buffer to the format Vosk expects (16kHz, 16-bit PCM)
        const audioData = this.convertAudioForVosk(audioBuffer);

        this.voskRecognizer.acceptWaveform(audioData);
        const result = this.voskRecognizer.result();
        return result.text || '';
      } else if (this.asrEngine === 'whisper') {
        return await this.transcribeWithWhisper(audioBuffer);
      } else {
        console.warn('Unsupported ASR engine:', this.asrEngine);
        return '';
      }
    } catch (error) {
      console.error('Error transcribing audio:', error);
      return '';
    }
  }

  async generateSpeech(text: string, voiceType: string = 'female'): Promise<Buffer> {
    try {
      if (this.ttsEngine === 'coqui') {
        return await this.generateCoquiSpeech(text, voiceType);
      } else if (this.ttsEngine === 'mozilla') {
        return await this.generateMozillaSpeech(text, voiceType);
      } else {
        console.warn('Unsupported TTS engine:', this.ttsEngine);
        return Buffer.alloc(0);
      }
    } catch (error) {
      console.error('Error generating speech:', error);
      return Buffer.alloc(0);
    }
  }

  private async transcribeWithWhisper(audioBuffer: Buffer): Promise<string> {
    try {
      // Use OpenAI Whisper API (free tier available)
      const axios = require('axios');
      const FormData = require('form-data');

      const formData = new FormData();
      // Convert buffer to WAV format if needed
      const wavBuffer = this.convertToWav(audioBuffer);
      formData.append('file', wavBuffer, { filename: 'audio.wav' });
      formData.append('model', 'whisper-1');
      formData.append('response_format', 'text');

      const response = await axios.post('https://api.openai.com/v1/audio/transcriptions', formData, {
        headers: {
          'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
          ...formData.getHeaders()
        },
        timeout: 30000
      });

      return response.data || '';
    } catch (error) {
      console.error('Error transcribing with Whisper:', error);
      return '';
    }
  }

  private convertToWav(audioBuffer: Buffer): Buffer {
    try {
      // Simple WAV header creation for 16-bit PCM, 16kHz, mono
      const sampleRate = 16000;
      const bitsPerSample = 16;
      const channels = 1;
      const dataSize = audioBuffer.length;
      const headerSize = 44;
      const totalSize = headerSize + dataSize;

      const wavBuffer = Buffer.alloc(headerSize + dataSize);

      // WAV header
      wavBuffer.write('RIFF', 0);
      wavBuffer.writeUInt32LE(totalSize - 8, 4);
      wavBuffer.write('WAVE', 8);
      wavBuffer.write('fmt ', 12);
      wavBuffer.writeUInt32LE(16, 16); // Subchunk1Size
      wavBuffer.writeUInt16LE(1, 20); // AudioFormat (PCM)
      wavBuffer.writeUInt16LE(channels, 22);
      wavBuffer.writeUInt32LE(sampleRate, 24);
      wavBuffer.writeUInt32LE(sampleRate * channels * bitsPerSample / 8, 28); // ByteRate
      wavBuffer.writeUInt16LE(channels * bitsPerSample / 8, 32); // BlockAlign
      wavBuffer.writeUInt16LE(bitsPerSample, 34);
      wavBuffer.write('data', 36);
      wavBuffer.writeUInt32LE(dataSize, 40);

      // Copy audio data
      audioBuffer.copy(wavBuffer, headerSize);

      return wavBuffer;
    } catch (error) {
      console.error('Error converting to WAV:', error);
      return audioBuffer; // Return original if conversion fails
    }
  }

  private convertAudioForVosk(audioBuffer: Buffer): Int16Array {
    try {
      // Assuming input is 16-bit PCM at 16kHz
      // Convert to the format Vosk expects
      const audioData = new Int16Array(audioBuffer.length / 2);
      for (let i = 0; i < audioData.length; i++) {
        audioData[i] = audioBuffer.readInt16LE(i * 2);
      }
      return audioData;
    } catch (error) {
      console.error('Error converting audio for Vosk:', error);
      return new Int16Array(0);
    }
  }

  private async generateCoquiSpeech(text: string, voiceType: string): Promise<Buffer> {
    try {
      // This is a placeholder implementation
      // In a real implementation, you would use the Coqui TTS library
      // For now, we'll create a simple audio buffer

      // Placeholder: create a simple beep sound
      const sampleRate = 16000;
      const duration = Math.max(1, text.length * 0.1); // Rough estimate
      const numSamples = Math.floor(sampleRate * duration);
      const audioBuffer = Buffer.alloc(numSamples * 2); // 16-bit samples

      // Generate a simple sine wave (placeholder)
      for (let i = 0; i < numSamples; i++) {
        const sample = Math.sin(2 * Math.PI * 440 * i / sampleRate) * 16384; // 440Hz tone
        audioBuffer.writeInt16LE(Math.floor(sample), i * 2);
      }

      return audioBuffer;
    } catch (error) {
      console.error('Error generating Coqui speech:', error);
      return Buffer.alloc(0);
    }
  }

  private async generateMozillaSpeech(text: string, voiceType: string): Promise<Buffer> {
    try {
      // Use Mozilla TTS (Coqui TTS) via HTTP API or local installation
      // For this implementation, we'll use a simple approach with espeak-ng as fallback
      // In production, you'd want to use a proper TTS service

      const { spawn } = require('child_process');
      const tempFile = `/tmp/tts_${Date.now()}.wav`;

      return new Promise((resolve, reject) => {
        // Use espeak-ng for basic TTS (available on most Linux systems)
        const voice = voiceType === 'male' ? 'en-us+m1' : 'en-us+f1';
        const espeak = spawn('espeak-ng', [
          '-v', voice,
          '-s', '150', // speed
          '-w', tempFile,
          text
        ]);

        espeak.on('close', (code: number) => {
          if (code === 0) {
            try {
              const fs = require('fs');
              const audioBuffer = fs.readFileSync(tempFile);
              fs.unlinkSync(tempFile); // Clean up temp file
              resolve(audioBuffer);
            } catch (error) {
              reject(error);
            }
          } else {
            reject(new Error(`espeak-ng exited with code ${code}`));
          }
        });

        espeak.on('error', (error: Error) => {
          console.warn('espeak-ng not available, using placeholder audio');
          // Fallback to simple tone generation
          resolve(this.generatePlaceholderAudio(text));
        });
      });
    } catch (error) {
      console.error('Error generating Mozilla speech:', error);
      return this.generatePlaceholderAudio(text);
    }
  }

  private generatePlaceholderAudio(text: string): Buffer {
    // Generate a simple beep pattern based on text length
    const sampleRate = 16000;
    const duration = Math.max(1, text.length * 0.1);
    const numSamples = Math.floor(sampleRate * duration);
    const audioBuffer = Buffer.alloc(numSamples * 2);

    for (let i = 0; i < numSamples; i++) {
      const frequency = 440 + (i % 100) * 2; // Varying frequency
      const sample = Math.sin(2 * Math.PI * frequency * i / sampleRate) * 8192;
      audioBuffer.writeInt16LE(Math.floor(sample), i * 2);
    }

    return audioBuffer;
  }

  async cleanup(): Promise<void> {
    if (this.voskRecognizer) {
      this.voskRecognizer.free();
    }
    if (this.voskModel) {
      this.voskModel.free();
    }
  }
}

export default new VoiceService();