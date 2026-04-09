import { Router, Request, Response } from 'express';
import axios from 'axios';
import multer from 'multer';
import FormData from 'form-data';

const router = Router();
const upload = multer({ limits: { fileSize: 100 * 1024 * 1024 } }); // 100MB max

const TTS_URL = () => process.env.TTS_SERVICE_URL || 'http://localhost:8003';

// ── Accepted audio formats for voice cloning ──────────────────────────────────
const CLONE_ALLOWED_MIMES = new Set([
  'audio/wav', 'audio/x-wav', 'audio/wave',
  'audio/mpeg', 'audio/mp3',
  'audio/mp4', 'audio/x-m4a',
  'audio/flac', 'audio/x-flac',
  'audio/ogg',
  'audio/webm',
]);

const CLONE_ALLOWED_EXTENSIONS = new Set([
  '.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm', '.mp4',
]);

const CLONE_MIN_SIZE = 50 * 1024;       // 50 KB — below this is too short / silent
const CLONE_MAX_SIZE = 20 * 1024 * 1024; // 20 MB — keeps cloning fast
const CLONE_MIN_DURATION_HINT_SIZE = 100 * 1024;  // ~3s of compressed audio at minimum
const CLONE_MAX_DURATION_HINT_SIZE = 10 * 1024 * 1024; // ~5min upper bound

// ─── GET /api/tts/preset-voices ──────────────────────────────────────────────
// Proxy to the TTS microservice's preset voice list.

router.get('/preset-voices', async (_req: Request, res: Response) => {
  try {
    const response = await axios.get(`${TTS_URL()}/preset-voices`, { timeout: 5000 });
    res.json(response.data);
  } catch (err: any) {
    console.error('[tts/preset-voices] Error:', err?.message);
    res.status(502).json({ error: 'TTS service unavailable' });
  }
});

// ─── POST /api/tts/synthesise ────────────────────────────────────────────────
// Proxy synthesis requests from the frontend (for preview playback).

router.post('/synthesise', async (req: Request, res: Response) => {
  try {
    const { text, voiceId, agentId } = req.body;
    if (!text) return res.status(400).json({ error: 'text is required' });

    const form = new FormData();
    form.append('text', text);
    form.append('voiceId', voiceId || 'preset-aria');
    if (agentId) form.append('agentId', agentId);

    const response = await axios.post(`${TTS_URL()}/synthesise`, form, {
      headers: form.getHeaders(),
      timeout: 10000,
    });

    res.json(response.data);
  } catch (err: any) {
    console.error('[tts/synthesise] Error:', err?.message);
    const status = err?.response?.status || 502;
    const msg = err?.response?.data?.detail || 'TTS synthesis failed';
    res.status(status).json({ error: msg });
  }
});

// ─── POST /api/tts/clone-voice ───────────────────────────────────────────────
// Proxy voice cloning upload to the TTS microservice.
// Includes pre-flight quality checks so customers get clear feedback
// when their reference audio won't produce a good clone.

router.post('/clone-voice', upload.single('file'), async (req: Request, res: Response) => {
  try {
    const file = req.file;
    if (!file) return res.status(400).json({ error: 'No audio file provided' });

    // ── Quality gate: format ────────────────────────────────────────────
    const ext = (file.originalname || '').toLowerCase().match(/\.\w+$/)?.[0] || '';
    const mime = (file.mimetype || '').toLowerCase();
    if (!CLONE_ALLOWED_MIMES.has(mime) && !CLONE_ALLOWED_EXTENSIONS.has(ext)) {
      return res.status(400).json({
        error: 'Unsupported audio format',
        detail: `Accepted formats: WAV, MP3, M4A, FLAC, OGG, WebM. You uploaded "${file.originalname}" (${mime}).`,
        tips: [
          'Export your recording as WAV or MP3 before uploading.',
          'Video files (.mp4 video, .mov) must be converted to audio-only first.',
        ],
      });
    }

    // ── Quality gate: file size (proxy for duration) ────────────────────
    if (file.size < CLONE_MIN_SIZE) {
      return res.status(400).json({
        error: 'Audio file is too short',
        detail: `The file is only ${Math.round(file.size / 1024)} KB. Voice cloning needs at least 5–10 seconds of clear speech.`,
        tips: [
          'Record at least 10 seconds of natural speech (reading a paragraph works well).',
          'Avoid recordings under 5 seconds — the model cannot capture enough vocal characteristics.',
        ],
      });
    }

    if (file.size > CLONE_MAX_SIZE) {
      return res.status(400).json({
        error: 'Audio file is too large',
        detail: `The file is ${Math.round(file.size / (1024 * 1024))} MB. Maximum is 20 MB.`,
        tips: [
          'Trim your recording to 30–60 seconds of the best, cleanest section.',
          'Use a lower bitrate (128 kbps MP3 is fine for voice cloning).',
          'You don\'t need a long recording — 30 seconds of clear speech gives excellent results.',
        ],
      });
    }

    // ── Quality gate: duration heuristic ────────────────────────────────
    // We can't decode audio server-side without ffmpeg, but file size gives
    // a reasonable proxy:
    //   - 128kbps MP3: 1 MB ≈ 65 seconds
    //   - 256kbps WAV: 1 MB ≈ 2 seconds (uncompressed)
    //   - 64kbps OGG:  1 MB ≈ 130 seconds
    // Below ~100 KB of compressed audio is almost certainly < 3 seconds.
    const isCompressed = /mp3|mpeg|ogg|m4a|webm|flac/.test(mime);
    if (isCompressed && file.size < CLONE_MIN_DURATION_HINT_SIZE) {
      return res.status(400).json({
        error: 'Audio recording appears too short for quality cloning',
        detail: 'Voice cloning works best with 10–60 seconds of clear speech.',
        tips: [
          'Read a full paragraph aloud — this gives the model enough vocal variety.',
          'Avoid single words or very short phrases.',
          'A 20-second clip of you speaking naturally produces the best results.',
        ],
      });
    }

    // ── Quality guidance (returned alongside success) ───────────────────
    const qualityWarnings: string[] = [];
    if (file.size > CLONE_MAX_DURATION_HINT_SIZE) {
      qualityWarnings.push(
        'Your file is quite large. Cloning uses only the first ~60 seconds — consider trimming to the best section for optimal quality.',
      );
    }

    // ── Forward to TTS microservice ─────────────────────────────────────
    const form = new FormData();
    form.append('file', file.buffer, {
      filename: file.originalname,
      contentType: file.mimetype,
    });

    const response = await axios.post(`${TTS_URL()}/clone-voice`, form, {
      headers: form.getHeaders(),
      timeout: 30000, // Cloning can take 5-15 seconds
    });

    // Return result with any quality warnings
    const result = response.data;
    if (qualityWarnings.length > 0) {
      result.qualityWarnings = qualityWarnings;
    }

    // Attach reference audio guidelines so the frontend can display them
    result.referenceAudioGuidelines = {
      idealDuration: '10–60 seconds',
      idealFormat: 'WAV or MP3 (128+ kbps)',
      bestPractices: [
        'Record in a quiet room with minimal background noise.',
        'Speak naturally at a conversational pace — don\'t read slowly or rush.',
        'Use a headset mic or phone held close to your mouth, not a laptop mic across the room.',
        'Read a paragraph of text (e.g. a news article) rather than repeating one phrase.',
        'Avoid music, TV, or other voices in the background.',
        'Phone recordings work if you\'re in a quiet space — speakerphone recordings usually don\'t.',
      ],
    };

    res.json(result);
  } catch (err: any) {
    console.error('[tts/clone-voice] Error:', err?.message);
    const status = err?.response?.status || 502;
    const msg = err?.response?.data?.detail || 'Voice cloning failed';

    // Add helpful context for common TTS service failures
    const tips: string[] = [];
    if (status === 502 || status === 503) {
      tips.push('The TTS service may be starting up. Please try again in a moment.');
    } else if (msg.toLowerCase().includes('audio') || msg.toLowerCase().includes('format')) {
      tips.push('Try converting your file to WAV format (16kHz, mono) before uploading.');
    }

    res.status(status).json({ error: msg, ...(tips.length ? { tips } : {}) });
  }
});

export default router;
