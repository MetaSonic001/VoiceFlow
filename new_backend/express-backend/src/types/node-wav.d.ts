declare module 'node-wav' {
  export interface WavFile {
    sampleRate: number;
    bitDepth: number;
    channels: number;
    length: number;
    buffer: Buffer;
  }

  export function decode(buffer: Buffer): WavFile;
  export function encode(buffer: Buffer, options: { sampleRate: number; bitDepth: number; channels: number }): Buffer;
}