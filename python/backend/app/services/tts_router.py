import io
import logging
import re
import wave
from collections.abc import AsyncGenerator

import httpx
from pydub import AudioSegment

from app.config import settings

logger = logging.getLogger("voiceflow.tts_router")
_SENTENCE_END_RE = re.compile(r"[.!?](?:\s|$)")


class TTSRouter:
    async def synthesize(self, text: str, engine: str, voice_id: str, speed: float = 1.0) -> bytes:
        """Return full audio bytes (WAV/MP3 depending on engine)."""
        engine_name = (engine or "kokoro").lower()
        if engine_name == "edge":
            raise ValueError("edge synthesis is handled by app.routes.tts")
        if engine_name == "kokoro":
            return await self._synthesize_kokoro(text=text, voice_id=voice_id, speed=speed)
        if engine_name == "piper":
            return await self._synthesize_piper(text=text, voice_id=voice_id, speed=speed)
        if engine_name == "orpheus":
            return await self._synthesize_orpheus(text=text, voice_id=voice_id, speed=speed)
        raise ValueError(f"Unsupported TTS engine: {engine_name}")

    async def synthesize_streaming(
        self,
        text_stream: AsyncGenerator[str, None],
        engine: str,
        voice_id: str,
    ) -> AsyncGenerator[bytes, None]:
        """Buffer token stream by sentence or 64-token window and yield audio chunks."""
        buffer: list[str] = []
        token_count = 0

        async for chunk in text_stream:
            if not chunk:
                continue
            buffer.append(chunk)
            token_count += len(chunk.split())

            current = "".join(buffer).strip()
            if not current:
                continue

            if token_count >= 64 or _SENTENCE_END_RE.search(current):
                yield await self.synthesize(current, engine=engine, voice_id=voice_id)
                buffer.clear()
                token_count = 0

        if buffer:
            current = "".join(buffer).strip()
            if current:
                yield await self.synthesize(current, engine=engine, voice_id=voice_id)

    async def synthesize_mulaw(self, text: str, engine: str, voice_id: str, speed: float = 1.0) -> bytes:
        """Return μ-law 8kHz mono bytes for Twilio using pydub conversion."""
        audio_bytes = await self.synthesize(text=text, engine=engine, voice_id=voice_id, speed=speed)
        return self._wav_to_mulaw_8khz_mono(audio_bytes)

    async def _synthesize_kokoro(self, text: str, voice_id: str, speed: float) -> bytes:
        payload = {
            "model": "kokoro",
            "input": text,
            "voice": voice_id or "af_sky",
            "speed": speed,
            "response_format": "wav",
        }
        url = f"{settings.KOKORO_TTS_URL.rstrip('/')}/v1/audio/speech"

        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Kokoro synthesis transport error: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(f"Kokoro synthesis failed ({resp.status_code}): {resp.text[:400]}")
        return resp.content

    async def _synthesize_piper(self, text: str, voice_id: str, speed: float) -> bytes:
        base = settings.PIPER_TTS_URL.rstrip("/")
        payload = {
            "input": text,
            "voice": voice_id or "en_US-lessac-medium",
            "speed": speed,
            "response_format": "wav",
        }

        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(f"{base}/v1/audio/speech", json=payload)
            if resp.status_code != 200:
                logger.info("Piper /v1/audio/speech failed (%s), retrying /synthesize", resp.status_code)
                resp = await client.post(f"{base}/synthesize", json=payload)

        if resp.status_code != 200:
            raise RuntimeError(f"Piper synthesis failed ({resp.status_code}): {resp.text[:400]}")
        return resp.content

    async def _synthesize_orpheus(self, text: str, voice_id: str, speed: float) -> bytes:
        payload = {
            "model": "orpheus",
            "messages": [
                {
                    "role": "system",
                    "content": "Rewrite text for expressive speech using optional tags like <laugh>, <sigh>, <whisper> while preserving meaning.",
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.6,
            "max_tokens": 256,
        }

        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(settings.ORPHEUS_URL, json=payload)

        if resp.status_code != 200:
            raise RuntimeError(f"Orpheus request failed ({resp.status_code}): {resp.text[:400]}")

        data = resp.json()
        expressive_text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
            or text
        )
        return await self._synthesize_kokoro(text=expressive_text, voice_id=voice_id, speed=speed)

    @staticmethod
    def _wav_to_mulaw_8khz_mono(wav_bytes: bytes) -> bytes:
        source = AudioSegment.from_file(io.BytesIO(wav_bytes), format="wav")
        converted = source.set_channels(1).set_frame_rate(8000)

        out = io.BytesIO()
        converted.export(out, format="wav", codec="pcm_mulaw")
        out.seek(0)

        try:
            with wave.open(out, "rb") as wf:
                return wf.readframes(wf.getnframes())
        except Exception:
            logger.error("Failed to parse mu-law wav wrapper", exc_info=True)
            raise RuntimeError("mu-law conversion failed")
