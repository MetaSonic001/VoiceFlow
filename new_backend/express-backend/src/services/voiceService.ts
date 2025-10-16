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
        // Placeholder for Whisper integration
        console.log('Whisper ASR not yet implemented');
        return '';
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
      // Placeholder for Mozilla TTS implementation
      console.log('Mozilla TTS not yet fully implemented');

      // For now, return empty buffer
      return Buffer.alloc(0);
    } catch (error) {
      console.error('Error generating Mozilla speech:', error);
      return Buffer.alloc(0);
    }
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