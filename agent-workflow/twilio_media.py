import asyncio
import base64
import json
import logging
import os
from typing import Callable
import base64
import shutil
import subprocess
import tempfile
import audioop
import math
import time

# Optional dependencies: vosk
try:
    from vosk import Model, KaldiRecognizer
except Exception:
    Model = None
    KaldiRecognizer = None

# Optional TTS: pyttsx3 (offline). If not present, outbound streaming TTS falls back to call.update in app.py
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

logger = logging.getLogger(__name__)

class VoskASR:
    """Simple Vosk-based ASR wrapper. Expects 16kHz mono PCM16 audio frames.

    You should download a suitable Vosk model and point VOSK_MODEL_PATH
    to it (or place it in ./models/vosk-model).
    """
    def __init__(self, model_path: str = None):
        # Allow overriding the model path via environment variable VOSK_MODEL_PATH
        if model_path is None:
            model_path = os.getenv('VOSK_MODEL_PATH', './models/vosk-model')

        if Model is None:
            raise RuntimeError("Vosk is not installed. Please install via requirements.txt")

        if not os.path.exists(model_path):
            raise RuntimeError(f"Vosk model not found at: {model_path}. Please download and extract a model or set VOSK_MODEL_PATH.")

        self.model = Model(model_path)
        self.recognizer = None

    def new_recognizer(self, sample_rate: int = 16000):
        self.recognizer = KaldiRecognizer(self.model, sample_rate)

    def accept_audio_frame(self, pcm_bytes: bytes) -> str:
        """Accept raw PCM16 bytes; return interim or final text when available.
        Returns empty string if no partial/full text is ready.
        """
        if self.recognizer is None:
            self.new_recognizer()
        if self.recognizer.AcceptWaveform(pcm_bytes):
            res = json.loads(self.recognizer.Result())
            return res.get('text', '')
        else:
            # interim
            res = json.loads(self.recognizer.PartialResult())
            return res.get('partial', '')


class MediaStreamBridge:
    """
    Handles incoming Twilio Media Streams frames over a WebSocket.
    - decodes base64 audio chunks (raw PCM16 8kHz by default from Twilio)
    - resamples to 16kHz if needed (left as TODO / placeholder)
    - feeds audio to ASR
    - yields transcripts via an async queue
    """
    def __init__(self, asr: VoskASR):
        self.asr = asr
        self.queue = asyncio.Queue()
        # detect ffmpeg availability
        self.ffmpeg_path = shutil.which('ffmpeg')

    async def handle_twilio_frame(self, frame_json: dict):
        # frame_json: Twilio media frame
        # Example envelope: {"event":"media","media":{"track":"inbound","payload":"<base64>"}}
        evt = frame_json.get('event')
        if evt == 'media':
            payload = frame_json.get('media', {}).get('payload')
            if not payload:
                return
            try:
                raw = base64.b64decode(payload)
                # Convert Twilio audio format to PCM16 16kHz
                pcm16_16k = None
                try:
                    pcm16_16k = self._convert_to_pcm16_16k(raw)
                except Exception:
                    logger.exception('Failed to convert audio via ffmpeg/audioop; attempting to use raw payload')
                    pcm16_16k = raw

                # Feed to ASR
                text = self.asr.accept_audio_frame(pcm16_16k)
                if text:
                    await self.queue.put(text)
            except Exception as e:
                logger.exception(f"Failed to process media payload: {e}")
        elif evt == 'connected':
            logger.info('Twilio media stream connected')
        elif evt == 'closed':
            logger.info('Twilio media stream closed')

    async def transcripts(self):
        while True:
            t = await self.queue.get()
            yield t

    def _convert_to_pcm16_16k(self, raw_bytes: bytes) -> bytes:
        """Convert Twilio media payload (commonly PCMU 8k) to PCM16 16k using ffmpeg if available,
        otherwise fall back to audioop transformations (ulaw->lin then ratecv).
        Returns raw PCM16 little-endian bytes at 16kHz mono.
        """
        # If ffmpeg is available, use it for decoding/resampling
        if self.ffmpeg_path:
            # We assume Twilio sends PCMU (mulaw) 8k mono by default.
            # Use ffmpeg to read from stdin and output s16le 16k mono to stdout.
            cmd = [self.ffmpeg_path, '-f', 'mulaw', '-ar', '8000', '-ac', '1', '-i', 'pipe:0', '-f', 's16le', '-ar', '16000', '-ac', '1', 'pipe:1']
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            out, _ = proc.communicate(raw_bytes)
            if proc.returncode != 0:
                raise RuntimeError('ffmpeg conversion failed')
            return out

        # Fallback: use audioop to convert from mu-law (PCMU) to linear PCM then resample
        try:
            # u-law decode to 16-bit linear
            lin = audioop.ulaw2lin(raw_bytes, 2)
            # resample from 8000 to 16000
            converted, _ = audioop.ratecv(lin, 2, 1, 8000, 16000, None)
            return converted
        except Exception as e:
            # If conversion fails, just return original
            logger.exception(f'Fallback audio conversion failed: {e}')
            return raw_bytes


def synthesize_text_to_pcm16(text: str, sample_rate: int = 16000) -> bytes:
    """Synthesize `text` to raw PCM16 16k mono bytes.

    Uses pyttsx3 if available to render WAV then ffmpeg to convert to s16le 16k.
    Returns raw PCM bytes. Raises if synthesis not available.
    """
    if pyttsx3 is None:
        raise RuntimeError('pyttsx3 not installed; cannot synthesize offline TTS')

    # Use a temporary file for WAV output
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tf:
        wav_path = tf.name
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.save_to_file(text, wav_path)
        engine.runAndWait()

        # Convert WAV to raw PCM16 16k via ffmpeg if available
        ffmpeg_path = shutil.which('ffmpeg')
        if not ffmpeg_path:
            # Could read WAV and convert with wave module and audioop but prefer ffmpeg
            raise RuntimeError('ffmpeg not available to convert WAV to PCM16')

        cmd = [ffmpeg_path, '-i', wav_path, '-f', 's16le', '-ar', str(sample_rate), '-ac', '1', 'pipe:1']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        out, _ = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError('ffmpeg conversion of TTS output failed')
        return out
    finally:
        try:
            os.remove(wav_path)
        except Exception:
            pass


async def stream_pcm16_to_twilio_ws(websocket, pcm_bytes: bytes, sample_rate: int = 16000, chunk_ms: int = 20):
    """Stream raw PCM16 bytes to Twilio Media Stream websocket as outbound frames.

    Splits `pcm_bytes` into frames of length chunk_ms and sends each as a base64 payload
    with event 'media' and media.track='outbound'. Sleeps between frames according to sample rate.
    """
    # chunk size in bytes: sample_rate * (chunk_ms/1000) * 2 bytes per sample
    frame_samples = int(sample_rate * (chunk_ms / 1000.0))
    frame_bytes = frame_samples * 2
    total = len(pcm_bytes)
    offset = 0
    interval = chunk_ms / 1000.0
    while offset < total:
        chunk = pcm_bytes[offset: offset + frame_bytes]
        payload = base64.b64encode(chunk).decode('ascii')
        msg = {
            'event': 'media',
            'media': {
                'track': 'outbound',
                'payload': payload
            }
        }
        await websocket.send_text(json.dumps(msg))
        offset += frame_bytes
        # Sleep to simulate real-time playback
        await asyncio.sleep(interval)

