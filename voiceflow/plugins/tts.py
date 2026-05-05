"""
voiceflow.plugins.tts — TTS plugin base class and built-in implementations.

Available implementations:
  KokoroTTS    — local Kokoro TTS server (port 8880), natural sounding
  SarvamTTS    — Sarvam AI bulbul:v1, 22 Indian languages
  EdgeTTS      — Microsoft Edge TTS (free, cloud, 400+ voices)
  ElevenLabsTTS — ElevenLabs (cloud, best quality, costly)
  PiperTTS     — Piper TTS local server (port 8890)
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger("voiceflow.tts")


class TTSPlugin(ABC):
    """Base class for all TTS implementations. Returns WAV bytes."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        speed: float = 1.0,
        language_code: Optional[str] = None,
    ) -> bytes:
        """Synthesize text to WAV audio bytes."""
        ...


class KokoroTTS(TTSPlugin):
    """
    Kokoro TTS — self-hosted local server.
    Start: docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu
    """

    def __init__(self, voice_id: str = "af_bella", host: str = "localhost", port: int = 8880):
        self.voice_id = voice_id
        self.base_url = f"http://{host}:{port}"

    async def synthesize(self, text: str, speed: float = 1.0, language_code: Optional[str] = None) -> bytes:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/audio/speech",
                    json={"model": "kokoro", "input": text, "voice": self.voice_id,
                          "speed": speed, "response_format": "wav"},
                )
                if resp.status_code == 200:
                    return resp.content
        except Exception as exc:
            logger.warning("[KokoroTTS] failed: %s", exc)
        return b""


class SarvamTTS(TTSPlugin):
    """
    Sarvam AI bulbul:v1 — 22 Indian languages.
    Get API key: https://dashboard.sarvam.ai
    """

    def __init__(self, api_key: str, language_code: str = "hi-IN", speaker: str = "meera"):
        self.api_key = api_key
        self.language_code = language_code
        self.speaker = speaker

    async def synthesize(self, text: str, speed: float = 1.0, language_code: Optional[str] = None) -> bytes:
        import base64
        import httpx
        lang = language_code or self.language_code
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.sarvam.ai/text-to-speech",
                    headers={"api-subscription-key": self.api_key, "Content-Type": "application/json"},
                    json={"inputs": [text[:1000]], "target_language_code": lang,
                          "speaker": self.speaker, "model": "bulbul:v1",
                          "pace": speed, "enable_preprocessing": True},
                )
                if resp.status_code == 200:
                    audio_b64 = resp.json().get("audios", [""])[0]
                    if audio_b64:
                        return base64.b64decode(audio_b64)
        except Exception as exc:
            logger.warning("[SarvamTTS] failed: %s", exc)
        return b""


class EdgeTTS(TTSPlugin):
    """
    Microsoft Edge TTS — free, cloud, 400+ voices.
    Install: pip install edge-tts
    """

    def __init__(self, voice: str = "en-IN-NeerjaNeural"):
        self.voice = voice

    async def synthesize(self, text: str, speed: float = 1.0, language_code: Optional[str] = None) -> bytes:
        try:
            import edge_tts
            import io
            communicate = edge_tts.Communicate(text, self.voice)
            buf = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
            return buf.getvalue()
        except ImportError:
            raise ImportError("edge-tts is required: pip install edge-tts")
        except Exception as exc:
            logger.warning("[EdgeTTS] failed: %s", exc)
            return b""


class ElevenLabsTTS(TTSPlugin):
    """
    ElevenLabs — best voice quality, cloud, paid.
    Install: pip install elevenlabs
    """

    def __init__(self, api_key: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL"):
        self.api_key = api_key
        self.voice_id = voice_id

    async def synthesize(self, text: str, speed: float = 1.0, language_code: Optional[str] = None) -> bytes:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                    headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
                    json={"text": text, "model_id": "eleven_multilingual_v2",
                          "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}},
                )
                if resp.status_code == 200:
                    return resp.content
        except Exception as exc:
            logger.warning("[ElevenLabsTTS] failed: %s", exc)
        return b""
