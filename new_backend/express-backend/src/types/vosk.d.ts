declare module 'vosk' {
  export class Model {
    constructor(modelPath: string);
    free(): void;
  }

  export interface RecognizerOptions {
    model: Model;
    sampleRate: number;
  }

  export interface RecognitionResult {
    text: string;
  }

  export class Recognizer {
    constructor(options: RecognizerOptions);
    acceptWaveform(audioData: Int16Array): boolean;
    result(): RecognitionResult;
    free(): void;
  }
}