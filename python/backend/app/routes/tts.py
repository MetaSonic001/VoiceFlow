"""
/api/tts routes - Edge-first synthesis with Chatterbox local fallback.

Engines:
  - Edge TTS (primary): fast cloud synthesis for preset voices
  - Chatterbox TTS (fallback): local synthesis and voice cloning
"""

import asyncio
import base64
import io
import logging
import os
import tempfile
import uuid
from collections import OrderedDict

import edge_tts
import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger("voiceflow.tts")

PREVIEW_SENTENCE = (
    "Hello! I'm your AI voice assistant. I can help answer questions about your "
    "company, guide customers through your products, and provide real-time support "
    "in a natural, conversational tone. Let me know how you'd like to get started!"
)

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

CHATTERBOX_VOICE_LIST = [
    {
        "id": "chatterbox-default",
        "name": "Chatterbox Local",
        "gender": "Neutral",
        "style": "Natural local synthesis",
        "language": "en-US",
        "engine": "chatterbox",
    }
]

_chatterbox_model = None
_chatterbox_available = False
_chatterbox_lock = asyncio.Lock()

_clone_prompts: OrderedDict[str, str] = OrderedDict()
_max_clone_prompts = 20

CLONE_CONFIRMATION_SENTENCES = [
    "Hello! This is your cloned voice. How does it sound to you?",
    "I can help answer questions, guide customers, and provide support - all in your voice.",
    "The quick brown fox jumps over the lazy dog. Every letter of the alphabet, clear as day.",
]


def _detect_chatterbox_device() -> str:
    try:
        import torch
    except Exception:
        return "cpu"

    if torch.cuda.is_available():
        return "cuda"

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"

    return "cpu"


async def _get_chatterbox_model():
    global _chatterbox_model, _chatterbox_available

    async with _chatterbox_lock:
        if _chatterbox_model is not None:
            return _chatterbox_model

        try:
            from chatterbox.tts import ChatterboxTTS

            device = _detect_chatterbox_device()
            logger.info("Loading Chatterbox-TTS on %s", device)

            def _load():
                return ChatterboxTTS.from_pretrained(device=device)

            _chatterbox_model = await asyncio.to_thread(_load)
            _chatterbox_available = True
            logger.info("Chatterbox-TTS loaded successfully")
            return _chatterbox_model
        except Exception as exc:
            logger.warning("Chatterbox-TTS failed to load: %s", exc)
            _chatterbox_available = False
            return None


def _wav_to_b64(wav_array: np.ndarray, sample_rate: int) -> str:
    buf = io.BytesIO()
    sf.write(buf, wav_array, sample_rate, format="WAV")
    return base64.b64encode(buf.getvalue()).decode()


def _normalize_wav_array(wav_obj) -> np.ndarray:
    if hasattr(wav_obj, "detach"):
        wav_array = wav_obj.detach().cpu().numpy()
    else:
        wav_array = np.asarray(wav_obj)

    wav_array = np.squeeze(wav_array)
    if wav_array.ndim != 1:
        wav_array = wav_array.reshape(-1)

    return wav_array.astype(np.float32, copy=False)


def resolve_edge_voice(voice_id: str) -> str:
    return EDGE_VOICES.get(voice_id, "en-US-AriaNeural")


def is_chatterbox_voice(voice_id: str) -> bool:
    return voice_id.startswith("chatterbox-")


def is_clone_voice(voice_id: str) -> bool:
    return voice_id.startswith("clone-")


def _clone_id_from_voice_id(voice_id: str) -> str:
    return voice_id.replace("clone-", "", 1)


def _get_clone_prompt_path(clone_id: str) -> str | None:
    path = _clone_prompts.get(clone_id)
    if path and os.path.exists(path):
        return path
    return None


def _store_clone_prompt(clone_id: str, prompt_path: str) -> None:
    _clone_prompts[clone_id] = prompt_path
    _clone_prompts.move_to_end(clone_id)

    while len(_clone_prompts) > _max_clone_prompts:
        old_clone_id, old_path = _clone_prompts.popitem(last=False)
        try:
            if os.path.exists(old_path):
                os.unlink(old_path)
            logger.info("Evicted old cloned prompt: %s", old_clone_id)
        except Exception:
            logger.warning("Failed cleaning old cloned prompt file: %s", old_clone_id)


def _drop_clone_prompt(clone_id: str) -> None:
    old_path = _clone_prompts.pop(clone_id, None)
    if old_path and os.path.exists(old_path):
        try:
            os.unlink(old_path)
        except Exception:
            logger.warning("Failed deleting cloned prompt file for %s", clone_id)


async def _synthesise_edge(text: str, voice_id: str) -> dict | JSONResponse:
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
            "engine": "edge",
            "charCount": len(text),
        }
    except Exception as exc:
        logger.exception("Edge TTS synthesis failed")
        return JSONResponse({"error": f"Edge TTS failed: {exc}"}, status_code=503)


async def _synthesise_chatterbox(
    text: str,
    voice_id: str = "",
    audio_prompt_path: str | None = None,
) -> dict | JSONResponse:
    model = await _get_chatterbox_model()
    if model is None:
        return JSONResponse({"error": "Chatterbox model not available"}, status_code=503)

    prompt_path = audio_prompt_path
    if prompt_path is None and is_clone_voice(voice_id):
        clone_id = _clone_id_from_voice_id(voice_id)
        prompt_path = _get_clone_prompt_path(clone_id)
        if not prompt_path:
            return JSONResponse({"error": "Clone not found. Please re-upload your audio."}, status_code=404)

    try:
        def _generate():
            kwargs = {"text": text}
            if prompt_path:
                kwargs["audio_prompt_path"] = prompt_path
            wav = model.generate(**kwargs)
            wav_array = _normalize_wav_array(wav)
            return wav_array, int(model.sr)

        wav_array, sample_rate = await asyncio.to_thread(_generate)
        audio_b64 = _wav_to_b64(wav_array, sample_rate)

        engine = "chatterbox-clone" if prompt_path else "chatterbox"
        return {
            "audioUrl": f"data:audio/wav;base64,{audio_b64}",
            "voiceId": voice_id,
            "engine": engine,
            "charCount": len(text),
        }
    except Exception as exc:
        logger.exception("Chatterbox synthesis failed")
        return JSONResponse({"error": f"Chatterbox synthesis failed: {exc}"}, status_code=500)


async def _synthesise_clone(text: str, voice_id: str) -> dict | JSONResponse:
    return await _synthesise_chatterbox(text=text, voice_id=voice_id)


@router.get("/preset-voices")
async def preset_voices():
    voices = EDGE_VOICE_LIST + CHATTERBOX_VOICE_LIST
    return {
        "voices": voices,
        "previewSentence": PREVIEW_SENTENCE,
        "chatterboxAvailable": _chatterbox_available or _chatterbox_model is None,
    }


@router.post("/preview")
async def preview_voice(body: dict):
    voice_id = body.get("voiceId", "preset-aria")
    text = body.get("text", PREVIEW_SENTENCE)

    if is_clone_voice(voice_id):
        return await _synthesise_clone(text, voice_id)

    if is_chatterbox_voice(voice_id):
        return await _synthesise_chatterbox(text, voice_id)

    edge_result = await _synthesise_edge(text, voice_id)
    if not isinstance(edge_result, JSONResponse):
        return edge_result

    logger.info("Edge preview failed, falling back to Chatterbox")
    chatterbox_result = await _synthesise_chatterbox(text, "chatterbox-default")
    if not isinstance(chatterbox_result, JSONResponse):
        return chatterbox_result

    return edge_result


@router.post("/synthesise")
async def synthesise(body: dict):
    text = body.get("text")
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    voice_id = body.get("voiceId", "")

    if is_clone_voice(voice_id):
        clone_result = await _synthesise_clone(text, voice_id)
        if not isinstance(clone_result, JSONResponse):
            return clone_result
        logger.info("Clone synthesis failed, attempting fallback engines")

    if is_chatterbox_voice(voice_id):
        chatterbox_result = await _synthesise_chatterbox(text, voice_id)
        if not isinstance(chatterbox_result, JSONResponse):
            return chatterbox_result
        logger.info("Chatterbox direct voice failed, attempting Edge fallback")

    edge_result = await _synthesise_edge(text, voice_id)
    if not isinstance(edge_result, JSONResponse):
        return edge_result

    logger.info("Edge synthesis failed, falling back to Chatterbox")
    chatterbox_result = await _synthesise_chatterbox(text, "chatterbox-default")
    if not isinstance(chatterbox_result, JSONResponse):
        return chatterbox_result

    return edge_result


@router.post("/clone-voice")
async def clone_voice(
    file: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
):
    """
    Clone a voice from an uploaded audio sample.
    Accepts either multipart field name "file" or "audio".
    """
    uploaded = file or audio
    if uploaded is None:
        return JSONResponse({"error": "No audio file provided"}, status_code=400)

    content = await uploaded.read()
    if len(content) > 20 * 1024 * 1024:
        return JSONResponse({"error": "Audio file is too large (max 20MB)"}, status_code=400)

    suffix = "." + (uploaded.filename or "audio.wav").rsplit(".", 1)[-1]
    clone_id = str(uuid.uuid4())[:12]
    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            temp_path = tmp.name

        _store_clone_prompt(clone_id, temp_path)

        samples = []
        clone_voice_id = f"clone-{clone_id}"
        for sentence in CLONE_CONFIRMATION_SENTENCES:
            result = await _synthesise_clone(sentence, clone_voice_id)
            if isinstance(result, JSONResponse):
                _drop_clone_prompt(clone_id)
                return result
            samples.append({"text": sentence, "audioUrl": result["audioUrl"]})

        return {
            "cloneId": clone_id,
            "samples": samples,
            "message": "Voice cloned successfully via Chatterbox",
            "engine": "chatterbox",
        }
    except Exception as exc:
        logger.exception("Chatterbox voice cloning failed")
        _drop_clone_prompt(clone_id)
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        return JSONResponse({"error": f"Voice cloning failed: {exc}"}, status_code=500)


@router.post("/clone-preview")
async def clone_preview(body: dict):
    clone_id = body.get("cloneId", "")
    text = body.get("text", "")

    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    if not clone_id:
        return JSONResponse({"error": "cloneId is required"}, status_code=400)

    return await _synthesise_clone(text, f"clone-{clone_id}")
