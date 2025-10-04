import asyncio
import base64
import json
import logging
import os
from typing import Callable

# Optional dependencies: vosk
try:
    from vosk import Model, KaldiRecognizer
except Exception:
    Model = None
    KaldiRecognizer = None

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

    async def handle_twilio_frame(self, frame_json: dict):
        # frame_json: Twilio media frame
        # Example envelope: {"event":"media","media":{"track":"inbound","payload":"<base64>"}}
        evt = frame_json.get('event')
        if evt == 'media':
            payload = frame_json.get('media', {}).get('payload')
            if not payload:
                return
            try:
                pcm = base64.b64decode(payload)
                # Vosk expects 16kHz PCM16; Twilio Media Streams default is 8kHz PCMU/PCMA
                # For a full implementation we should decode and resample (e.g., via soundfile or ffmpeg)
                # For now assume input is PCM16 16kHz (if you configure Twilio to send that)
                text = self.asr.accept_audio_frame(pcm)
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
