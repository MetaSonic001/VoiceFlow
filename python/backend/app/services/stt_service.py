"""
STT (Speech-to-Text) Service.

Primary engine : faster-whisper (tiny or distil-small.en) — CPU, int8
Secondary engine: Vosk KaldiRecognizer (offline, auto-downloads 40 MB model)
Fallback engine : Groq Whisper API
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import struct
import wave
import zipfile
from typing import Optional

from app.config import settings

logger = logging.getLogger("voiceflow.stt")

_WHISPER_MODEL = None
_WHISPER_AVAILABLE = False

_VOSK_MODEL = None
_VOSK_AVAILABLE = False


def _load_faster_whisper() -> None:
    global _WHISPER_MODEL, _WHISPER_AVAILABLE
    try:
        from faster_whisper import WhisperModel

        _WHISPER_MODEL = WhisperModel("tiny", device="cpu", compute_type="int8")
        _WHISPER_AVAILABLE = True
        logger.info("[stt] faster-whisper loaded (device=cpu, int8)")
    except ImportError:
        logger.info("[stt] faster-whisper not installed")
    except Exception as exc:
        logger.warning("[stt] faster-whisper load failed: %s", exc)


def _load_vosk() -> None:
    global _VOSK_MODEL, _VOSK_AVAILABLE
    model_path = settings.VOSK_MODEL_PATH
    if not os.path.isdir(model_path):
        logger.info("[stt] Vosk model not found at %s; skipping Vosk", model_path)
        return
    try:
        from vosk import Model

        _VOSK_MODEL = Model(model_path)
        _VOSK_AVAILABLE = True
        logger.info("[stt] Vosk model loaded from %s", model_path)
    except ImportError:
        logger.info("[stt] vosk package not installed")
    except Exception as exc:
        logger.warning("[stt] Vosk model load failed: %s", exc)


def _pcm_bytes_to_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def _rms(pcm_bytes: bytes) -> float:
    """Compute root-mean-square energy of 16-bit PCM samples."""
    n = len(pcm_bytes) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm_bytes)
    return (sum(s * s for s in samples) / n) ** 0.5


class STTService:
    """Unified speech-to-text service used by both WebSocket and Twilio Media Streams paths."""

    async def initialize(self) -> None:
        """Download Vosk model if missing, then load both engines."""
        await self._ensure_vosk_model()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _load_faster_whisper)
        await loop.run_in_executor(None, _load_vosk)

    async def _ensure_vosk_model(self) -> None:
        model_path = settings.VOSK_MODEL_PATH
        if os.path.isdir(model_path):
            return

        url = settings.VOSK_MODEL_URL
        logger.info("[stt] Downloading Vosk model from %s …", url)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._download_and_extract_vosk, url, model_path)

    @staticmethod
    def _download_and_extract_vosk(url: str, model_path: str) -> None:
        import urllib.request

        zip_path = model_path + ".zip"
        parent = os.path.dirname(model_path) or "."
        os.makedirs(parent, exist_ok=True)

        try:
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(parent)
            # The zip usually produces a directory named like the zip stem
            extracted_name = os.path.splitext(os.path.basename(zip_path))[0]
            extracted_path = os.path.join(parent, extracted_name)
            if os.path.isdir(extracted_path) and extracted_path != model_path:
                os.rename(extracted_path, model_path)
            logger.info("[stt] Vosk model downloaded and extracted to %s", model_path)
        except Exception as exc:
            logger.error("[stt] Vosk download failed: %s", exc)
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        engine: str = "faster-whisper",
        groq_api_key: Optional[str] = None,
    ) -> str:
        """
        Transcribe raw PCM 16-bit mono bytes.

        engine priorities (auto-falls-back):
          1. faster-whisper (device='cpu', int8)
          2. vosk
          3. groq (if engine=='groq' and groq_api_key provided)
        """
        if engine == "groq" and groq_api_key:
            return await self._transcribe_groq(audio_bytes, sample_rate, groq_api_key)

        if _WHISPER_AVAILABLE:
            try:
                return await self._transcribe_faster_whisper(audio_bytes, sample_rate)
            except Exception as exc:
                logger.warning("[stt] faster-whisper failed, trying Vosk: %s", exc)

        if _VOSK_AVAILABLE:
            try:
                return await self._transcribe_vosk(audio_bytes, sample_rate)
            except Exception as exc:
                logger.warning("[stt] Vosk failed: %s", exc)

        if groq_api_key:
            return await self._transcribe_groq(audio_bytes, sample_rate, groq_api_key)

        return ""

    def create_vosk_recognizer(self, sample_rate: int = 16000):
        """
        Create a persistent KaldiRecognizer for streaming recognition.
        The returned recognizer should be reused across calls to
        transcribe_stream_chunk() for the same audio stream.
        Returns None if Vosk is not available.
        """
        if not _VOSK_AVAILABLE or _VOSK_MODEL is None:
            return None
        try:
            from vosk import KaldiRecognizer

            return KaldiRecognizer(_VOSK_MODEL, sample_rate)
        except Exception as exc:
            logger.warning("[stt] KaldiRecognizer creation failed: %s", exc)
            return None

    async def transcribe_stream_chunk(
        self,
        pcm_chunk: bytes,
        sample_rate: int = 16000,
        recognizer=None,
    ) -> Optional[str]:
        """
        Feed a PCM chunk to a persistent Vosk recognizer for partial/online recognition.
        Pass the recognizer returned by create_vosk_recognizer() to maintain state across
        chunks. If no recognizer is provided a temporary one is created (loses context).
        Returns partial transcript text or None if nothing ready yet.
        """
        if not _VOSK_AVAILABLE or _VOSK_MODEL is None:
            return None

        _rec = recognizer  # captured into closure

        loop = asyncio.get_event_loop()

        def _run() -> Optional[str]:
            rec = _rec
            if rec is None:
                from vosk import KaldiRecognizer

                rec = KaldiRecognizer(_VOSK_MODEL, sample_rate)
            if rec.AcceptWaveform(pcm_chunk):
                result = json.loads(rec.Result())
                return result.get("text") or None
            partial = json.loads(rec.PartialResult())
            text = partial.get("partial") or ""
            return text if text else None

        return await loop.run_in_executor(None, _run)

    async def _transcribe_faster_whisper(self, pcm_bytes: bytes, sample_rate: int) -> str:
        if not _WHISPER_AVAILABLE or _WHISPER_MODEL is None:
            return ""

        wav_bytes = _pcm_bytes_to_wav(pcm_bytes, sample_rate)

        def _run() -> str:
            buf = io.BytesIO(wav_bytes)
            segments, _ = _WHISPER_MODEL.transcribe(buf, language="en", vad_filter=True)
            return " ".join(seg.text for seg in segments).strip()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run)

    async def _transcribe_vosk(self, pcm_bytes: bytes, sample_rate: int) -> str:
        if not _VOSK_AVAILABLE or _VOSK_MODEL is None:
            return ""

        def _run() -> str:
            from vosk import KaldiRecognizer

            rec = KaldiRecognizer(_VOSK_MODEL, sample_rate)
            chunk_size = 4000
            for i in range(0, len(pcm_bytes), chunk_size):
                rec.AcceptWaveform(pcm_bytes[i : i + chunk_size])
            result = json.loads(rec.FinalResult())
            return result.get("text", "").strip()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run)

    async def _transcribe_groq(self, pcm_bytes: bytes, sample_rate: int, groq_api_key: str) -> str:
        import httpx

        wav_bytes = _pcm_bytes_to_wav(pcm_bytes, sample_rate)
        buf = io.BytesIO(wav_bytes)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {groq_api_key}"},
                    files={"file": ("audio.wav", buf, "audio/wav")},
                    data={"model": "whisper-large-v3-turbo", "language": "en"},
                )
                if resp.status_code == 200:
                    return resp.json().get("text", "").strip()
                logger.warning("[stt] Groq Whisper returned %s", resp.status_code)
        except Exception as exc:
            logger.warning("[stt] Groq Whisper request failed: %s", exc)
        return ""


# Module-level singleton
stt_service = STTService()
