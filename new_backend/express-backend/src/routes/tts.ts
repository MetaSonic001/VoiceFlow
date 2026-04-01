import { Router, Request, Response } from 'express';
import axios from 'axios';
import multer from 'multer';
import FormData from 'form-data';

const router = Router();
const upload = multer({ limits: { fileSize: 100 * 1024 * 1024 } }); // 100MB max

const TTS_URL = () => process.env.TTS_SERVICE_URL || 'http://localhost:8003';

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

router.post('/clone-voice', upload.single('file'), async (req: Request, res: Response) => {
  try {
    const file = req.file;
    if (!file) return res.status(400).json({ error: 'No audio file provided' });

    const form = new FormData();
    form.append('file', file.buffer, {
      filename: file.originalname,
      contentType: file.mimetype,
    });

    const response = await axios.post(`${TTS_URL()}/clone-voice`, form, {
      headers: form.getHeaders(),
      timeout: 30000, // Cloning can take 5-15 seconds
    });

    res.json(response.data);
  } catch (err: any) {
    console.error('[tts/clone-voice] Error:', err?.message);
    const status = err?.response?.status || 502;
    const msg = err?.response?.data?.detail || 'Voice cloning failed';
    res.status(status).json({ error: msg });
  }
});

export default router;
