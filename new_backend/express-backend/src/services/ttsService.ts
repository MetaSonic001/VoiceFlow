import axios from 'axios';
import FormData from 'form-data';

const TTS_URL = () => process.env.TTS_SERVICE_URL || 'http://localhost:8003';
const TTS_TIMEOUT = 2000; // 2-second timeout — never let TTS break a call

/**
 * Request speech synthesis from the Chatterbox TTS microservice.
 * Returns the presigned audio URL, or null if the service is unavailable.
 *
 * This is designed to be used in the Twilio voice loop where latency matters.
 * Falls back gracefully — a null return means the caller should use <Say>.
 */
export async function synthesiseForCall(
  text: string,
  voiceId: string,
  agentId?: string,
): Promise<string | null> {
  try {
    const form = new FormData();
    form.append('text', text);
    form.append('voiceId', voiceId);
    if (agentId) form.append('agentId', agentId);

    const res = await axios.post(`${TTS_URL()}/synthesise`, form, {
      headers: form.getHeaders(),
      timeout: TTS_TIMEOUT,
    });

    return res.data?.audioUrl || null;
  } catch (err: any) {
    // Non-fatal: log and fall back to <Say>
    console.warn(`[tts] Synthesis failed (falling back to <Say>): ${err?.message}`);
    return null;
  }
}
