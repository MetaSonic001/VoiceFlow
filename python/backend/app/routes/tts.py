"""
/api/tts routes — Dual TTS engine:
  • Qwen3-TTS 0.6B (local GPU) — premium custom voices + voice cloning
  • Edge TTS (Microsoft cloud) — 13 preset en-US voices, zero-GPU fallback
"""
import asyncio
import base64
import io
import logging
import tempfile
import wave

import edge_tts
import soundfile as sf
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger("voiceflow.tts")

PREVIEW_SENTENCE = (
    "Hello! I'm your AI voice assistant. I can help answer questions about your "
    "company, guide customers through your products, and provide real-time support "
    "in a natural, conversational tone. Let me know how you'd like to get started!"
)

# ── Edge TTS voice catalogue ──────────────────────────────────────────
EDGE_VOICES = {
    "": "en-US-AriaNeural",
    "preset-aria": "en-US-AriaNeural",
    "preset-ava": "en-US-AvaNeural",
    "preset-jenny": "en-US-JennyNeural",
    "preset-emma": "en-US-EmmaNeural",
    "preset-ana": "en-US-AnaNeural",
    "preset-michelle": "en-US-MichelleNeural",
    "preset-guy": "en-US-GuyNeural",
    "preset-brian": "en-US-BrianNeural",
    "preset-andrew": "en-US-AndrewNeural",
    "preset-christopher": "en-US-ChristopherNeural",
    "preset-eric": "en-US-EricNeural",
    "preset-roger": "en-US-RogerNeural",
    "preset-steffan": "en-US-SteffanNeural",
}

# ── Qwen3-TTS speaker catalogue (0.6B-CustomVoice) ────────────────────
QWEN_SPEAKERS = {
    "qwen-vivian": {"speaker": "Vivian", "language": "Chinese", "gender": "Female", "style": "Bright & edgy"},
    "qwen-serena": {"speaker": "Serena", "language": "Chinese", "gender": "Female", "style": "Warm & gentle"},
    "qwen-ryan": {"speaker": "Ryan", "language": "English", "gender": "Male", "style": "Dynamic & rhythmic"},
    "qwen-aiden": {"speaker": "Aiden", "language": "English", "gender": "Male", "style": "Sunny & clear"},
    "qwen-anna": {"speaker": "Ono_Anna", "language": "Japanese", "gender": "Female", "style": "Playful & nimble"},
    "qwen-sohee": {"speaker": "Sohee", "language": "Korean", "gender": "Female", "style": "Warm & emotional"},
}

EDGE_VOICE_LIST = [
    {"id": "preset-aria", "name": "Aria", "gender": "Female", "style": "Friendly & warm", "language": "en-US", "engine": "edge"},
    {"id": "preset-ava", "name": "Ava", "gender": "Female", "style": "Expressive & natural", "language": "en-US", "engine": "edge"},
    {"id": "preset-jenny", "name": "Jenny", "gender": "Female", "style": "Professional", "language": "en-US", "engine": "edge"},
    {"id": "preset-emma", "name": "Emma", "gender": "Female", "style": "Cheerful", "language": "en-US", "engine": "edge"},
    {"id": "preset-ana", "name": "Ana", "gender": "Female", "style": "Soft & gentle", "language": "en-US", "engine": "edge"},
    {"id": "preset-michelle", "name": "Michelle", "gender": "Female", "style": "Clear & confident", "language": "en-US", "engine": "edge"},
    {"id": "preset-guy", "name": "Guy", "gender": "Male", "style": "News anchor", "language": "en-US", "engine": "edge"},
    {"id": "preset-brian", "name": "Brian", "gender": "Male", "style": "Confident narrator", "language": "en-US", "engine": "edge"},
    {"id": "preset-andrew", "name": "Andrew", "gender": "Male", "style": "Warm & articulate", "language": "en-US", "engine": "edge"},
    {"id": "preset-christopher", "name": "Christopher", "gender": "Male", "style": "Authoritative", "language": "en-US", "engine": "edge"},
    {"id": "preset-eric", "name": "Eric (Edge)", "gender": "Male", "style": "Casual & relaxed", "language": "en-US", "engine": "edge"},
    {"id": "preset-roger", "name": "Roger", "gender": "Male", "style": "Deep & smooth", "language": "en-US", "engine": "edge"},
    {"id": "preset-steffan", "name": "Steffan", "gender": "Male", "style": "Smooth & clear", "language": "en-US", "engine": "edge"},
]

QWEN_VOICE_LIST = [
    {"id": "qwen-ryan", "name": "Ryan (Qwen3)", "gender": "Male", "style": "Dynamic & rhythmic", "language": "en-US", "engine": "qwen3"},
    {"id": "qwen-aiden", "name": "Aiden (Qwen3)", "gender": "Male", "style": "Sunny & clear", "language": "en-US", "engine": "qwen3"},
    {"id": "qwen-vivian", "name": "Vivian (Qwen3)", "gender": "Female", "style": "Bright & edgy", "language": "zh-CN", "engine": "qwen3"},
    {"id": "qwen-serena", "name": "Serena (Qwen3)", "gender": "Female", "style": "Warm & gentle", "language": "zh-CN", "engine": "qwen3"},
    {"id": "qwen-anna", "name": "Anna (Qwen3)", "gender": "Female", "style": "Playful & nimble", "language": "ja-JP", "engine": "qwen3"},
    {"id": "qwen-sohee", "name": "Sohee (Qwen3)", "gender": "Female", "style": "Warm & emotional", "language": "ko-KR", "engine": "qwen3"},
]


# ── Lazy-load Qwen3-TTS model (keeps VRAM free until first use) ───────
_qwen_model = None
_qwen_available = False
_qwen_lock = asyncio.Lock()


async def _get_qwen_model():
    """Lazy-load the Qwen3-TTS 0.6B-CustomVoice model on first call."""
    global _qwen_model, _qwen_available
    async with _qwen_lock:
        if _qwen_model is not None:
            return _qwen_model
        try:
            import torch
            from qwen_tts import Qwen3TTSModel
            logger.info("Loading Qwen3-TTS 0.6B-CustomVoice on GPU…")
            _qwen_model = Qwen3TTSModel.from_pretrained(
                "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
                device_map="cuda:0",
                dtype=torch.bfloat16,
            )
            _qwen_available = True
            logger.info("Qwen3-TTS loaded successfully")
            return _qwen_model
        except Exception as e:
            logger.warning(f"Qwen3-TTS failed to load: {e}")
            _qwen_available = False
            return None


# ── Lazy-load Qwen3-TTS Base model for voice cloning ──────────────────
_qwen_base_model = None
_qwen_base_lock = asyncio.Lock()


async def _get_qwen_base_model():
    """Lazy-load the Qwen3-TTS 0.6B-Base model for voice cloning."""
    global _qwen_base_model
    async with _qwen_base_lock:
        if _qwen_base_model is not None:
            return _qwen_base_model
        try:
            import torch
            from qwen_tts import Qwen3TTSModel
            logger.info("Loading Qwen3-TTS 0.6B-Base for voice cloning…")
            _qwen_base_model = Qwen3TTSModel.from_pretrained(
                "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                device_map="cuda:0",
                dtype=torch.bfloat16,
            )
            logger.info("Qwen3-TTS Base loaded for voice cloning")
            return _qwen_base_model
        except Exception as e:
            logger.warning(f"Qwen3-TTS Base failed to load: {e}")
            return None


def _wav_to_b64(wav_array, sample_rate: int) -> str:
    """Convert numpy audio array to base64 WAV string."""
    buf = io.BytesIO()
    sf.write(buf, wav_array, sample_rate, format="WAV")
    return base64.b64encode(buf.getvalue()).decode()


def resolve_edge_voice(voice_id: str) -> str:
    return EDGE_VOICES.get(voice_id, "en-US-AriaNeural")


def is_qwen_voice(voice_id: str) -> bool:
    return voice_id.startswith("qwen-")


def is_clone_voice(voice_id: str) -> bool:
    return voice_id.startswith("clone-")


# ── Routes ─────────────────────────────────────────────────────────────

@router.get("/preset-voices")
async def preset_voices():
    voices = QWEN_VOICE_LIST + EDGE_VOICE_LIST
    return {"voices": voices, "previewSentence": PREVIEW_SENTENCE, "qwenAvailable": _qwen_available or _qwen_model is None}


@router.post("/preview")
async def preview_voice(body: dict):
    """Generate a preview clip of a voice using a standard sample sentence."""
    voice_id = body.get("voiceId", "preset-aria")
    text = body.get("text", PREVIEW_SENTENCE)

    # Cloned voices
    if is_clone_voice(voice_id):
        return await _synthesise_clone(text, voice_id)

    # Qwen3-TTS voices
    if is_qwen_voice(voice_id):
        return await _synthesise_qwen(text, voice_id)

    # Edge TTS voices
    edge_voice = resolve_edge_voice(voice_id)
    try:
        communicate = edge_tts.Communicate(text, edge_voice)
        audio_bytes = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes.write(chunk["data"])

        audio_b64 = base64.b64encode(audio_bytes.getvalue()).decode()
        return {
            "audioUrl": f"data:audio/mp3;base64,{audio_b64}",
            "voice": edge_voice,
            "voiceId": voice_id,
        }
    except Exception as e:
        logger.exception("Edge TTS preview failed")
        return JSONResponse({"error": f"Preview failed: {e}"}, status_code=500)


async def _synthesise_qwen(text: str, voice_id: str, instruct: str = "") -> dict:
    """Synthesise using Qwen3-TTS CustomVoice model."""
    model = await _get_qwen_model()
    if model is None:
        return JSONResponse({"error": "Qwen3-TTS model not available"}, status_code=503)

    speaker_info = QWEN_SPEAKERS.get(voice_id)
    if not speaker_info:
        return JSONResponse({"error": f"Unknown Qwen voice: {voice_id}"}, status_code=400)

    try:
        loop = asyncio.get_event_loop()
        wavs, sr = await loop.run_in_executor(None, lambda: model.generate_custom_voice(
            text=text,
            language=speaker_info["language"],
            speaker=speaker_info["speaker"],
            instruct=instruct or "",
        ))
        audio_b64 = _wav_to_b64(wavs[0], sr)
        return {
            "audioUrl": f"data:audio/wav;base64,{audio_b64}",
            "voice": speaker_info["speaker"],
            "voiceId": voice_id,
            "engine": "qwen3",
            "charCount": len(text),
        }
    except Exception as e:
        logger.exception("Qwen3-TTS synthesis failed")
        return JSONResponse({"error": f"Qwen3-TTS failed: {e}"}, status_code=500)


async def _synthesise_clone(text: str, voice_id: str) -> dict:
    """Synthesise using a previously cached clone prompt (clone-<id>)."""
    clone_id = voice_id.replace("clone-", "", 1)
    prompt = _clone_prompts.get(clone_id)
    if prompt is None:
        return JSONResponse({"error": "Clone not found. Please re-upload your audio."}, status_code=404)

    model = await _get_qwen_base_model()
    if model is None:
        return JSONResponse({"error": "Qwen3-TTS Base model not available"}, status_code=503)

    try:
        loop = asyncio.get_event_loop()
        wavs, sr = await loop.run_in_executor(None, lambda: model.generate_voice_clone(
            text=text,
            language="English",
            voice_clone_prompt=prompt,
        ))
        return {
            "audioUrl": f"data:audio/wav;base64,{_wav_to_b64(wavs[0], sr)}",
            "voiceId": voice_id,
            "engine": "qwen3-clone",
            "charCount": len(text),
        }
    except Exception as e:
        logger.exception("Cloned voice synthesis failed")
        return JSONResponse({"error": f"Clone synthesis failed: {e}"}, status_code=500)


@router.post("/synthesise")
async def synthesise(body: dict):
    text = body.get("text")
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    voice_id = body.get("voiceId", "")
    instruct = body.get("instruct", "")

    # Cloned voices
    if is_clone_voice(voice_id):
        clone_result = await _synthesise_clone(text, voice_id)
        if not isinstance(clone_result, JSONResponse):
            return clone_result
        logger.info("Clone synthesis failed, falling back to other engines")

    # Qwen3-TTS voices
    if is_qwen_voice(voice_id):
        result = await _synthesise_qwen(text, voice_id, instruct)
        if not isinstance(result, JSONResponse):
            return result
        # Qwen failed — fall through to Edge TTS
        logger.info("Qwen3-TTS failed, falling back to Edge TTS")

    # Edge TTS (default / fallback)
    edge_voice = resolve_edge_voice(voice_id)
    try:
        communicate = edge_tts.Communicate(text, edge_voice)
        audio_bytes = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes.write(chunk["data"])

        audio_b64 = base64.b64encode(audio_bytes.getvalue()).decode()
        return {
            "audioUrl": f"data:audio/mp3;base64,{audio_b64}",
            "voice": edge_voice,
            "engine": "edge",
            "charCount": len(text),
        }
    except Exception as e:
        logger.exception("Edge TTS synthesis failed")
        return JSONResponse({"error": f"TTS synthesis failed: {e}"}, status_code=500)


# ── Clone prompt cache (server-side, keyed by UUID) ────────────────────
import uuid as _uuid

_clone_prompts: dict[str, object] = {}

CLONE_CONFIRMATION_SENTENCES = [
    "Hello! This is your cloned voice. How does it sound to you?",
    "I can help answer questions, guide customers, and provide support — all in your voice.",
    "The quick brown fox jumps over the lazy dog. Every letter of the alphabet, clear as day.",
]


@router.post("/clone-voice")
async def clone_voice(file: UploadFile = File(...)):
    """Clone a voice from an audio sample. Returns 3 confirmation clips + a cloneId for further testing."""
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        return JSONResponse({"error": "Audio file is too large (max 20MB)"}, status_code=400)

    model = await _get_qwen_base_model()
    if model is None:
        return JSONResponse(
            {"error": "Voice cloning requires Qwen3-TTS Base model, which failed to load. Check GPU availability."},
            status_code=503,
        )

    try:
        import os
        suffix = "." + (file.filename or "audio.wav").rsplit(".", 1)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        loop = asyncio.get_event_loop()

        # Build reusable clone prompt from the reference audio
        prompt = await loop.run_in_executor(None, lambda: model.create_voice_clone_prompt(
            ref_audio=tmp_path,
            ref_text="",
            x_vector_only_mode=True,
        ))
        os.unlink(tmp_path)

        # Generate 3 confirmation clips
        samples = []
        for sentence in CLONE_CONFIRMATION_SENTENCES:
            wavs, sr = await loop.run_in_executor(None, lambda s=sentence: model.generate_voice_clone(
                text=s, language="English", voice_clone_prompt=prompt,
            ))
            samples.append({
                "text": sentence,
                "audioUrl": f"data:audio/wav;base64,{_wav_to_b64(wavs[0], sr)}",
            })

        # Store prompt for subsequent preview requests
        clone_id = str(_uuid.uuid4())[:12]
        _clone_prompts[clone_id] = prompt

        return {
            "cloneId": clone_id,
            "samples": samples,
            "message": "Voice cloned successfully via Qwen3-TTS",
            "engine": "qwen3",
        }
    except Exception as e:
        logger.exception("Qwen3-TTS voice cloning failed")
        return JSONResponse({"error": f"Voice cloning failed: {e}"}, status_code=500)


@router.post("/clone-preview")
async def clone_preview(body: dict):
    """Generate audio from a custom sentence using a previously cloned voice."""
    clone_id = body.get("cloneId", "")
    text = body.get("text", "")
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    prompt = _clone_prompts.get(clone_id)
    if prompt is None:
        return JSONResponse({"error": "Clone not found. Please re-upload your audio."}, status_code=404)

    model = await _get_qwen_base_model()
    if model is None:
        return JSONResponse({"error": "Qwen3-TTS Base model not available"}, status_code=503)

    try:
        loop = asyncio.get_event_loop()
        wavs, sr = await loop.run_in_executor(None, lambda: model.generate_voice_clone(
            text=text, language="English", voice_clone_prompt=prompt,
        ))
        return {
            "audioUrl": f"data:audio/wav;base64,{_wav_to_b64(wavs[0], sr)}",
            "engine": "qwen3",
            "charCount": len(text),
        }
    except Exception as e:
        logger.exception("Clone preview failed")
        return JSONResponse({"error": f"Clone preview failed: {e}"}, status_code=500)
