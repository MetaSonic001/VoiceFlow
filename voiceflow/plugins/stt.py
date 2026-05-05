"""
voiceflow.plugins.stt — STT plugin base class and built-in implementations.

Available implementations:
  WhisperSTT       — faster-whisper, CPU, int8, auto language detect
  SarvamSTT        — Sarvam AI saarika:v2, 22 Indian languages + Hinglish
  GroqSTT          — Groq Whisper API (cloud, fast, English-primary)
  DeepgramSTT      — Deepgram Nova (cloud, streaming, multilingual)
  VoskSTT          — Vosk offline (no internet, ~40MB model)

All accept raw 16-bit mono PCM bytes and return a transcript string.
"""
from __future__ import annotations

import asyncio
import io
import logging
import wave
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger("voiceflow.stt")


class STTPlugin(ABC):
    """Base class for all STT implementations."""

    @abstractmethod
    async def transcribe(
        self,
        pcm_bytes: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> str:
        """Transcribe raw PCM audio. Returns transcript string."""
        ...

    def _pcm_to_wav(self, pcm_bytes: bytes, sample_rate: int) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return buf.getvalue()


class WhisperSTT(STTPlugin):
    """
    faster-whisper: CPU int8, auto language detection.
    Install: pip install faster-whisper
    """

    def __init__(self, model_size: str = "tiny", language: Optional[str] = None):
        self.model_size = model_size
        self.language = language
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000, language: Optional[str] = None) -> str:
        wav = self._pcm_to_wav(pcm_bytes, sample_rate)
        lang = language or self.language
        loop = asyncio.get_event_loop()
        def _run():
            model = self._load()
            segments, info = model.transcribe(io.BytesIO(wav), language=lang, vad_filter=True)
            return " ".join(s.text for s in segments).strip()
        return await loop.run_in_executor(None, _run)


class SarvamSTT(STTPlugin):
    """
    Sarvam AI saarika:v2 — 22 Indian languages + Hinglish code-switching.
    Install: pip install sarvamai  (or use directly via HTTP)
    Get API key: https://dashboard.sarvam.ai
    """

    def __init__(self, api_key: str, language: Optional[str] = None):
        self.api_key = api_key
        self.language = language  # e.g. "hi-IN", None = auto-detect

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000, language: Optional[str] = None) -> str:
        import httpx
        wav = self._pcm_to_wav(pcm_bytes, sample_rate)
        lang = language or self.language
        form: dict = {"model": "saarika:v2", "with_timestamps": "false"}
        if lang:
            form["language_code"] = lang
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.sarvam.ai/speech-to-text",
                    headers={"api-subscription-key": self.api_key},
                    files={"file": ("audio.wav", io.BytesIO(wav), "audio/wav")},
                    data=form,
                )
                if resp.status_code == 200:
                    return resp.json().get("transcript", "").strip()
        except Exception as exc:
            logger.warning("[SarvamSTT] failed: %s", exc)
        return ""


class GroqSTT(STTPlugin):
    """
    Groq Whisper API — cloud-hosted, fast, primarily English.
    Install: (no extra package needed, uses httpx)
    """

    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo"):
        self.api_key = api_key
        self.model = model

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000, language: Optional[str] = None) -> str:
        import httpx
        wav = self._pcm_to_wav(pcm_bytes, sample_rate)
        data: dict = {"model": self.model}
        if language:
            data["language"] = language
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"file": ("audio.wav", io.BytesIO(wav), "audio/wav")},
                    data=data,
                )
                if resp.status_code == 200:
                    return resp.json().get("text", "").strip()
        except Exception as exc:
            logger.warning("[GroqSTT] failed: %s", exc)
        return ""


class DeepgramSTT(STTPlugin):
    """
    Deepgram Nova — cloud streaming STT, multilingual.
    Install: pip install deepgram-sdk
    """

    def __init__(self, api_key: str, model: str = "nova-2", language: str = "en-IN"):
        self.api_key = api_key
        self.model = model
        self.language = language

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000, language: Optional[str] = None) -> str:
        import httpx
        wav = self._pcm_to_wav(pcm_bytes, sample_rate)
        lang = language or self.language
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://api.deepgram.com/v1/listen?model={self.model}&language={lang}&smart_format=true",
                    headers={"Authorization": f"Token {self.api_key}", "Content-Type": "audio/wav"},
                    content=wav,
                )
                if resp.status_code == 200:
                    channels = resp.json().get("results", {}).get("channels", [])
                    if channels:
                        alts = channels[0].get("alternatives", [])
                        if alts:
                            return alts[0].get("transcript", "").strip()
        except Exception as exc:
            logger.warning("[DeepgramSTT] failed: %s", exc)
        return ""


class VoskSTT(STTPlugin):
    """
    Vosk — fully offline, CPU-only, ~40MB model download.
    Install: pip install vosk
    """

    def __init__(self, model_path: str = "vosk-model-small-en-us"):
        self.model_path = model_path
        self._model = None

    def _load(self):
        if self._model is None:
            from vosk import Model
            self._model = Model(self.model_path)
        return self._model

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000, language: Optional[str] = None) -> str:
        loop = asyncio.get_event_loop()
        def _run():
            import json
            from vosk import KaldiRecognizer
            model = self._load()
            rec = KaldiRecognizer(model, sample_rate)
            for i in range(0, len(pcm_bytes), 4000):
                rec.AcceptWaveform(pcm_bytes[i:i + 4000])
            return json.loads(rec.FinalResult()).get("text", "").strip()
        return await loop.run_in_executor(None, _run)
