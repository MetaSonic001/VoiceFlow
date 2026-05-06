import hashlib
import io
import logging
import os
import random
import re
import wave
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
from pydub import AudioSegment

from app.config import settings

logger = logging.getLogger("voiceflow.tts_router")
_SENTENCE_END_RE = re.compile(r"[.!?](?:\s|$)")

# ── Phrase cache (pre-recorded audio inserts, Bolna-style cost reduction) ─────
# Common filler phrases are synthesised once, stored on disk, and reused.
# Cuts TTS API costs by ~40% at scale. Key: hash of (text, engine, voice_id).
_PHRASE_CACHE_DIR = Path(os.getenv("TTS_CACHE_DIR", "/tmp/voiceflow_tts_cache"))
_PHRASE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Filler phrases (played while LLM is thinking, >800ms threshold) ───────────
# Pre-generated once per voice_id and served from disk for zero-latency playback.
_FILLER_PHRASES = [
    "Let me check that for you.",
    "One moment please.",
    "Hmm, let me see.",
    "Sure, just a second.",
    "Great question, let me look into that.",
    "Right, let me find that information.",
]
_FILLER_THRESHOLD_MS = 800   # play filler if LLM hasn't started responding in 800ms

# ── Initial ringing tone ──────────────────────────────────────────────────────
# Played before the first agent utterance to simulate a natural call pickup feel.
_RINGING_SOUND_FILE = Path(os.getenv(
    "RINGING_SOUND_FILE",
    str(Path(__file__).parent.parent / "static" / "audio" / "ringing.mp3"),
))

# ── Background ambient sounds ─────────────────────────────────────────────────
# Shipped as filenames under a configurable directory.
# Mixed at -18dB with TTS output before encoding to μ-law for Twilio.
_AMBIENT_DIR = Path(os.getenv("AMBIENT_SOUNDS_DIR", str(Path(__file__).parent.parent / "static" / "ambient")))
_AMBIENT_SOUNDS = {
    "office": "office.mp3",
    "cafe": "cafe.mp3",
    "call_center": "call_center.mp3",
    "street": "street.mp3",
    "nature": "nature.mp3",
}
# dB level for ambient mix — quiet enough not to interfere with speech
_AMBIENT_GAIN_DB = -20


class TTSRouter:
    async def synthesize(
        self,
        text: str,
        engine: str,
        voice_id: str,
        speed: float = 1.0,
        ambient_sound: str | None = None,
        sarvam_api_key: str | None = None,
        language_code: str | None = None,
    ) -> bytes:
        """
        Return full audio bytes (WAV).

        Engines: kokoro | piper | orpheus | sarvam | edge
        Phrase cache: SHA-256 keyed, stored on disk — avoids re-synthesising common phrases.
        Ambient sound: mixed at -18dB if ambient_sound is set (office/cafe/call_center/street).
        """
        engine_name = (engine or "kokoro").lower()

        # ── Phrase cache lookup ───────────────────────────────────────────────
        cache_key = hashlib.sha256(f"{engine_name}:{voice_id}:{language_code}:{text}".encode()).hexdigest()
        cache_file = _PHRASE_CACHE_DIR / f"{cache_key}.wav"
        if cache_file.exists():
            audio_bytes = cache_file.read_bytes()
        else:
            if engine_name == "edge":
                audio_bytes = await self._synthesize_edge(text=text, voice_id=voice_id or "en-US-AriaNeural")
            elif engine_name == "sarvam" and sarvam_api_key:
                audio_bytes = await self._synthesize_sarvam(
                    text=text, voice_id=voice_id, api_key=sarvam_api_key,
                    language_code=language_code or "en-IN",
                )
            elif engine_name == "kokoro":
                audio_bytes = await self._synthesize_kokoro(text=text, voice_id=voice_id, speed=speed)
            elif engine_name == "piper":
                audio_bytes = await self._synthesize_piper(text=text, voice_id=voice_id, speed=speed)
            elif engine_name == "orpheus":
                audio_bytes = await self._synthesize_orpheus(text=text, voice_id=voice_id, speed=speed)
            else:
                raise ValueError(f"Unsupported TTS engine: {engine_name}")

            # Store in phrase cache (only cache short phrases to avoid disk bloat)
            if len(text) <= 200 and audio_bytes:
                try:
                    cache_file.write_bytes(audio_bytes)
                except Exception:
                    pass  # cache write failure is non-fatal

        # ── Ambient sound mixing ──────────────────────────────────────────────
        if ambient_sound and audio_bytes:
            audio_bytes = self._mix_ambient(audio_bytes, ambient_sound)

        return audio_bytes

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

            # Flush on sentence boundaries or every ~64 whitespace-split tokens to
            # balance audio latency (~1-2 s) against synthesis request overhead.
            if token_count >= 64 or _SENTENCE_END_RE.search(current):
                yield await self.synthesize(current, engine=engine, voice_id=voice_id)
                buffer.clear()
                token_count = 0

        if buffer:
            current = "".join(buffer).strip()
            if current:
                yield await self.synthesize(current, engine=engine, voice_id=voice_id)

    async def synthesize_mulaw(self, text: str, engine: str, voice_id: str, speed: float = 1.0, **kwargs) -> bytes:
        """Return μ-law 8kHz mono bytes for Twilio using pydub conversion."""
        audio_bytes = await self.synthesize(text=text, engine=engine, voice_id=voice_id, speed=speed, **kwargs)
        return self._wav_to_mulaw_8khz_mono(audio_bytes)

    # ── Filler phrase system ──────────────────────────────────────────────────

    async def get_filler(self, engine: str, voice_id: str) -> bytes:
        """
        Return a random pre-cached filler phrase as WAV bytes.

        Filler phrases are synthesised once per (engine, voice_id) combination
        and stored on disk.  Subsequent calls are instant (disk read ≈ 0ms).
        If no filler has been pre-generated yet, generates all phrases lazily.
        """
        for phrase in random.sample(_FILLER_PHRASES, len(_FILLER_PHRASES)):
            cache_key = hashlib.sha256(f"{engine}:{voice_id}:filler:{phrase}".encode()).hexdigest()
            cache_file = _PHRASE_CACHE_DIR / f"{cache_key}.wav"
            if cache_file.exists():
                return cache_file.read_bytes()
        # None cached — synthesise one now and cache the rest in the background
        import asyncio
        phrase = random.choice(_FILLER_PHRASES)
        audio = await self.synthesize(phrase, engine=engine, voice_id=voice_id)
        cache_key = hashlib.sha256(f"{engine}:{voice_id}:filler:{phrase}".encode()).hexdigest()
        cache_file = _PHRASE_CACHE_DIR / f"{cache_key}.wav"
        try:
            cache_file.write_bytes(audio)
        except Exception:
            pass
        asyncio.create_task(self.pre_generate_fillers(engine=engine, voice_id=voice_id))
        return audio

    async def pre_generate_fillers(self, engine: str, voice_id: str) -> None:
        """Pre-generate and cache all filler phrases for a given voice."""
        for phrase in _FILLER_PHRASES:
            cache_key = hashlib.sha256(f"{engine}:{voice_id}:filler:{phrase}".encode()).hexdigest()
            cache_file = _PHRASE_CACHE_DIR / f"{cache_key}.wav"
            if not cache_file.exists():
                try:
                    audio = await self.synthesize(phrase, engine=engine, voice_id=voice_id)
                    cache_file.write_bytes(audio)
                except Exception as exc:
                    logger.debug("[tts] filler pre-generate failed '%s': %s", phrase, exc)

    def get_ringing_audio(self) -> bytes | None:
        """Return the initial ringing sound WAV bytes, or None if file not found."""
        if _RINGING_SOUND_FILE.exists():
            try:
                seg = AudioSegment.from_file(str(_RINGING_SOUND_FILE))
                out = io.BytesIO()
                seg.export(out, format="wav")
                return out.getvalue()
            except Exception as exc:
                logger.debug("[tts] ringing sound load failed: %s", exc)
        return None

    async def _synthesize_edge(self, text: str, voice_id: str) -> bytes:
        """Call Edge TTS and return WAV bytes (converted from MP3 via pydub)."""
        import io as _io
        import edge_tts

        # Handle both new "edge-en-US-AriaNeural" format and bare ShortName
        neural_name = voice_id.removeprefix("edge-") if voice_id.startswith("edge-") else voice_id
        if not neural_name.endswith("Neural"):
            neural_name = "en-US-AriaNeural"  # safe fallback

        communicate = edge_tts.Communicate(text, neural_name)
        mp3_buf = _io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_buf.write(chunk["data"])

        mp3_bytes = mp3_buf.getvalue()
        if not mp3_bytes:
            raise RuntimeError("Edge TTS returned empty audio")

        # Convert MP3 → WAV so it fits the phrase cache convention (all WAV)
        try:
            seg = AudioSegment.from_file(_io.BytesIO(mp3_bytes), format="mp3")
            wav_buf = _io.BytesIO()
            seg.export(wav_buf, format="wav")
            return wav_buf.getvalue()
        except Exception:
            # If conversion fails, return raw MP3 bytes; downstream handles both
            return mp3_bytes

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

    async def _synthesize_sarvam(
        self, text: str, voice_id: str, api_key: str, language_code: str = "en-IN"
    ) -> bytes:
        """
        Sarvam AI TTS — 22 Indian languages + Hinglish.

        Sarvam API docs: https://docs.sarvam.ai/api-reference-docs/text-to-speech
        Model: bulbul:v1  — 8kHz telephony-optimised.
        language_code: hi-IN, ta-IN, te-IN, kn-IN, ml-IN, bn-IN, mr-IN, gu-IN, en-IN, etc.
        """
        payload = {
            "inputs": [text],
            "target_language_code": language_code,
            "speaker": voice_id or "meera",   # Sarvam speaker names: meera, arvind, amol, etc.
            "model": "bulbul:v1",
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 8000,
            "enable_preprocessing": True,
            "eng_interpolation_wt": 123,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.sarvam.ai/text-to-speech",
                    headers={
                        "api-subscription-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Sarvam returns {"audios": ["<base64-wav>", ...]}
                    import base64
                    audio_b64 = data.get("audios", [""])[0]
                    if audio_b64:
                        return base64.b64decode(audio_b64)
                logger.warning("[tts] Sarvam TTS returned %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("[tts] Sarvam TTS failed: %s", exc)
        return b""

    def _mix_ambient(self, speech_wav: bytes, ambient_name: str) -> bytes:
        """
        Mix a speech WAV with a looped ambient background track at -18dB.
        Returns WAV bytes. Falls back to original speech on any error.

        Ships 5 ambient presets: office, cafe, call_center, street, silence.
        Background sounds should be placed in AMBIENT_SOUNDS_DIR as .mp3 files.
        """
        ambient_file = _AMBIENT_DIR / _AMBIENT_SOUNDS.get(ambient_name, "")
        if not ambient_file.exists():
            logger.debug("[tts] ambient file not found: %s — skipping mix", ambient_file)
            return speech_wav
        try:
            speech = AudioSegment.from_file(io.BytesIO(speech_wav), format="wav")
            ambient = AudioSegment.from_file(str(ambient_file))
            # Loop ambient to match speech length, then duck to -18dB
            loops = (len(speech) // len(ambient)) + 2
            ambient_loop = (ambient * loops)[: len(speech)]
            ambient_loop = ambient_loop + _AMBIENT_GAIN_DB  # reduce volume

            mixed = speech.overlay(ambient_loop)
            out = io.BytesIO()
            mixed.export(out, format="wav")
            return out.getvalue()
        except Exception as exc:
            logger.warning("[tts] ambient mix failed (%s): %s", ambient_name, exc)
            return speech_wav

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
