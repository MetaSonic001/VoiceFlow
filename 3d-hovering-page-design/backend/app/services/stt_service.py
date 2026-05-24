"""
STT (Speech-to-Text) Service.

Primary engine : faster-whisper (tiny or distil-small.en) — CPU, int8
Secondary engine: Vosk KaldiRecognizer (offline, auto-downloads 40 MB model)
Fallback engine : Groq Whisper API
Indian languages: Sarvam AI (pip install sarvamai) — 22 Indian languages + Hinglish
Noise reduction : noisereduce (spectral gating, CPU-only, applied before STT)

Mid-call language switching:
  - Detected language is stored in Redis at call_lang:{call_sid} with 2h TTL
  - Callers pass call_sid to transcribe_bytes(); on language change an event is emitted
  - get_call_language(call_sid) returns the current detected language for a call
  - streaming_orchestrator passes the stored language back for subsequent turns so
    Sarvam / Whisper stay locked to the correct code-switched language
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
from typing import Any, Optional

import numpy as np

from app.config import settings

logger = logging.getLogger("voiceflow.stt")

_WHISPER_MODEL = None
_WHISPER_AVAILABLE = False

_VOSK_MODEL = None
_VOSK_AVAILABLE = False

_NOISEREDUCE_AVAILABLE = False

# ── Noise reduction availability check ───────────────────────────────────────

try:
    import noisereduce  # noqa: F401
    _NOISEREDUCE_AVAILABLE = True
    logger.info("[stt] noisereduce available — noise suppression enabled")
except ImportError:
    logger.info("[stt] noisereduce not installed — skipping noise suppression")


# ── Adaptive noise calibration ────────────────────────────────────────────────
# Per-call noise floor estimate.  Key: call_sid, value: estimated noise RMS.
# Calibration uses the first 500ms of audio to classify the environment and
# select the appropriate prop_decrease level:
#   quiet/office  → 0.4 (light filtering)
#   typical call  → 0.6
#   noisy street  → 0.85 (heavy filtering for India market/street calls)
_noise_floor_cache: dict[str, float] = {}  # call_sid → noise_floor_rms


def _estimate_noise_floor(pcm_bytes: bytes) -> float:
    """
    Estimate background noise RMS from a short PCM segment (first 500ms recommended).
    Uses the quietest 10% of 20ms frames as a noise floor estimator.
    """
    n = len(pcm_bytes) // 2
    if n == 0:
        return 0.0
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    frame_size = int(0.02 * 16000)  # 20ms frames
    rms_values = []
    for i in range(0, len(samples) - frame_size, frame_size):
        frame = samples[i:i + frame_size]
        rms_values.append(float(np.sqrt(np.mean(frame ** 2))))
    if not rms_values:
        return 0.0
    rms_values.sort()
    quiet_frames = rms_values[: max(1, len(rms_values) // 10)]
    return sum(quiet_frames) / len(quiet_frames)


def _noise_prop_decrease(noise_floor: float) -> float:
    """
    Map a noise floor RMS to an appropriate noisereduce prop_decrease.
    Quiet office: low floor → gentle filter (0.4)
    Busy street / market: high floor → aggressive filter (0.85)
    """
    if noise_floor < 0.01:      # very quiet
        return 0.40
    elif noise_floor < 0.04:    # typical call center
        return 0.60
    elif noise_floor < 0.10:    # outdoor / vehicle
        return 0.75
    else:                        # market / street
        return 0.85


def calibrate_noise_floor(call_sid: str, first_500ms_pcm: bytes) -> float:
    """
    Store noise floor estimate for a call.  Call once at call start with the
    first 500ms of audio.  Subsequent calls to _apply_noise_reduction will
    use the stored estimate for adaptive filtering.
    """
    floor = _estimate_noise_floor(first_500ms_pcm)
    _noise_floor_cache[call_sid] = floor
    logger.debug("[stt] calibrated noise floor for %s: %.4f (prop_decrease=%.2f)",
                 call_sid, floor, _noise_prop_decrease(floor))
    return floor


def clear_noise_calibration(call_sid: str) -> None:
    """Remove cached noise floor when a call ends."""
    _noise_floor_cache.pop(call_sid, None)


# ── Per-call language tracking ────────────────────────────────────────────────
# Supports mid-call language switching: detected language stored in Redis so that
# subsequent STT turns can continue in the same language (or follow the switch).
# Key: call_lang:{call_sid}  Value: BCP-47 code, e.g. "hi-IN", "en-IN"
# TTL: 2 hours (auto-expires after call ends)

async def _redis_key_set(key: str, value: str, ttl: int = 7200) -> None:
    try:
        import redis.asyncio as aioredis
        r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=2, decode_responses=True)
        await r.setex(key, ttl, value)
        await r.aclose()
    except Exception:
        pass


async def _redis_key_get(key: str) -> Optional[str]:
    try:
        import redis.asyncio as aioredis
        r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=2, decode_responses=True)
        val = await r.get(key)
        await r.aclose()
        return val
    except Exception:
        return None


async def update_call_language(call_sid: str, language_code: str) -> None:
    """Persist the detected/active language for an ongoing call."""
    await _redis_key_set(f"call_lang:{call_sid}", language_code, ttl=7200)
    logger.info("[stt] call %s language updated → %s", call_sid, language_code)


async def get_call_language(call_sid: str) -> Optional[str]:
    """Return the most recently detected language for an ongoing call, or None."""
    if not call_sid:
        return None
    return await _redis_key_get(f"call_lang:{call_sid}")


def _apply_noise_reduction(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    call_sid: Optional[str] = None,
) -> bytes:
    """
    Apply adaptive spectral-gating noise reduction to raw 16-bit mono PCM bytes.

    If call_sid is provided and a noise floor has been calibrated via
    calibrate_noise_floor(), the prop_decrease is chosen automatically based on
    the measured environment (office vs. street vs. vehicle).
    Sarvam AI / OmniDim both suppress noise at this layer for India call quality.
    """
    if not _NOISEREDUCE_AVAILABLE or not pcm_bytes:
        return pcm_bytes
    try:
        import noisereduce as nr
        if call_sid and call_sid in _noise_floor_cache:
            prop_decrease = _noise_prop_decrease(_noise_floor_cache[call_sid])
        else:
            prop_decrease = 0.75  # safe default
        samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        reduced = nr.reduce_noise(
            y=samples, sr=sample_rate,
            prop_decrease=prop_decrease,
            stationary=False,
        )
        out = (reduced * 32768.0).clip(-32768, 32767).astype(np.int16)
        return out.tobytes()
    except Exception as exc:
        logger.debug("[stt] noise reduction skipped: %s", exc)
        return pcm_bytes


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
        sarvam_api_key: Optional[str] = None,
        language: Optional[str] = None,
        call_sid: Optional[str] = None,
    ) -> str:
        """
        Transcribe raw PCM 16-bit mono bytes.

        engine priorities (auto-falls-back):
          1. sarvam  — 22 Indian languages + Hinglish (requires SARVAM_API_KEY)
          2. faster-whisper (device='cpu', int8) — also returns detected language_code
          3. vosk
          4. groq (if engine=='groq' and groq_api_key provided)

        Mid-call language switching:
          If call_sid is provided, the detected language is stored/updated in Redis at
          call_lang:{call_sid}.  On subsequent turns, pass call_sid and omit `language`
          — the service automatically loads the cached language so STT stays consistent
          within a code-switching conversation.

        Noise reduction (noisereduce spectral gating) is applied before transcription
        with adaptive prop_decrease based on the call's calibrated noise floor.
        Pass call_sid to enable per-call adaptive calibration.
        """
        # ── Resolve language for this turn ────────────────────────────────────
        # If language not explicitly provided, check Redis for the call's active language
        effective_language = language
        if call_sid and not effective_language:
            effective_language = await get_call_language(call_sid)

        # Apply adaptive noise reduction
        audio_bytes = await asyncio.get_event_loop().run_in_executor(
            None, _apply_noise_reduction, audio_bytes, sample_rate, call_sid
        )

        transcript = ""

        if engine == "sarvam" and sarvam_api_key:
            transcript, detected_lang = await self._transcribe_sarvam(
                audio_bytes, sample_rate, sarvam_api_key, effective_language
            )
        elif engine == "groq" and groq_api_key:
            transcript = await self._transcribe_groq(audio_bytes, sample_rate, groq_api_key)
            detected_lang = effective_language  # Groq doesn't return language
        elif _WHISPER_AVAILABLE:
            try:
                transcript, detected_lang = await self._transcribe_faster_whisper(
                    audio_bytes, sample_rate, effective_language
                )
            except Exception as exc:
                logger.warning("[stt] faster-whisper failed, trying Vosk: %s", exc)
                detected_lang = effective_language
                if _VOSK_AVAILABLE:
                    try:
                        transcript = await self._transcribe_vosk(audio_bytes, sample_rate)
                    except Exception:
                        pass
                elif groq_api_key:
                    transcript = await self._transcribe_groq(audio_bytes, sample_rate, groq_api_key)
        elif _VOSK_AVAILABLE:
            try:
                transcript = await self._transcribe_vosk(audio_bytes, sample_rate)
                detected_lang = effective_language
            except Exception as exc:
                logger.warning("[stt] Vosk failed: %s", exc)
                detected_lang = effective_language
        elif groq_api_key:
            transcript = await self._transcribe_groq(audio_bytes, sample_rate, groq_api_key)
            detected_lang = effective_language
        else:
            detected_lang = effective_language

        # ── Persist detected language for mid-call switching ──────────────────
        if call_sid and detected_lang and detected_lang != effective_language:
            await update_call_language(call_sid, detected_lang)
        elif call_sid and detected_lang and not effective_language:
            await update_call_language(call_sid, detected_lang)

        return transcript

    def create_vosk_recognizer(self, sample_rate: int = 16000) -> Optional[Any]:
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

    async def finalize_vosk_recognizer(self, recognizer: Any) -> str:
        """
        Drain a streaming Vosk KaldiRecognizer after a speech segment.
        Returns the final text for that segment (may be empty).
        Call before creating a new recognizer for the next utterance.
        """
        if recognizer is None or not _VOSK_AVAILABLE:
            return ""

        def _fin() -> str:
            import json

            try:
                data = json.loads(recognizer.FinalResult())
                return (data.get("text") or "").strip()
            except Exception:
                return ""

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _fin)

    async def _transcribe_sarvam(
        self, pcm_bytes: bytes, sample_rate: int, api_key: str, language: Optional[str] = None
    ) -> tuple[str, Optional[str]]:
        """
        Transcribe using Sarvam AI — 22 Indian languages + Hinglish code-switching.

        Sarvam API docs: https://docs.sarvam.ai/api-reference-docs/speech-to-text
        Model: saarika:v2 — 8kHz telephony-optimised, mulaw/PCM, real-time WebSocket.
        language_code examples: hi-IN, ta-IN, te-IN, kn-IN, ml-IN, bn-IN, mr-IN,
                                  gu-IN, pa-IN, od-IN, ur-IN, en-IN (auto-detect if None)
        Returns (transcript, detected_language_code).
        """
        import httpx

        wav_bytes = _pcm_bytes_to_wav(pcm_bytes, sample_rate)
        buf = io.BytesIO(wav_bytes)
        try:
            form_data = {
                "model": "saarika:v2",
                "with_timestamps": "false",
                "with_disfluencies": "false",
            }
            if language:
                form_data["language_code"] = language
            # else: Sarvam auto-detects language

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.sarvam.ai/speech-to-text",
                    headers={"api-subscription-key": api_key},
                    files={"file": ("audio.wav", buf, "audio/wav")},
                    data=form_data,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Sarvam returns {"transcript": "...", "language_code": "hi-IN", ...}
                    transcript = data.get("transcript", "").strip()
                    detected_lang = data.get("language_code")
                    if detected_lang and detected_lang != language:
                        logger.info("[stt] sarvam detected language switch: %s → %s", language, detected_lang)
                    return transcript, detected_lang
                logger.warning("[stt] Sarvam STT returned %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            logger.warning("[stt] Sarvam STT request failed: %s", exc)
        return "", language

    async def _transcribe_faster_whisper(
        self,
        pcm_bytes: bytes,
        sample_rate: int,
        language: Optional[str] = None,
    ) -> tuple[str, Optional[str]]:
        """
        Transcribe with faster-whisper.
        Returns (transcript, detected_language_code).
        When language is None, whisper auto-detects and the detected code is returned
        so the caller can update per-call language state for mid-call switching.
        """
        if not _WHISPER_AVAILABLE or _WHISPER_MODEL is None:
            return "", language

        wav_bytes = _pcm_bytes_to_wav(pcm_bytes, sample_rate)

        def _run() -> tuple[str, Optional[str]]:
            buf = io.BytesIO(wav_bytes)
            segments, info = _WHISPER_MODEL.transcribe(
                buf,
                language=language,  # None → auto-detect
                vad_filter=True,
            )
            detected = getattr(info, "language", None)
            if detected and detected != (language or "en"):
                logger.info("[stt] whisper detected language=%s (prob=%.2f)",
                            detected, getattr(info, "language_probability", 0))
            transcript = " ".join(seg.text for seg in segments).strip()
            return transcript, detected or language

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
