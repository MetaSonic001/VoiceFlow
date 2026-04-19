"""
/api/tts routes — CPU-only TTS routing.

Engines:
  - Edge TTS (cloud fallback)
  - Kokoro (primary CPU)
  - Piper (CPU fallback)
  - Orpheus (emotion text rewrite + Kokoro synthesis)
"""

import base64
import io
import logging

import edge_tts
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.services.tts_router import TTSRouter

router = APIRouter()
logger = logging.getLogger("voiceflow.tts")
_tts_router = TTSRouter()

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
]

CPU_VOICE_LIST = [
    {"id": "kokoro-af_sky", "name": "Kokoro Sky", "gender": "Neutral", "style": "Natural CPU", "language": "en-US", "engine": "kokoro"},
    {"id": "piper-en_US-lessac-medium", "name": "Piper Lessac", "gender": "Neutral", "style": "Fast ONNX CPU", "language": "en-US", "engine": "piper"},
    {"id": "orpheus-af_sky", "name": "Orpheus Expressive", "gender": "Neutral", "style": "Emotion-tagged", "language": "en-US", "engine": "orpheus"},
]


def resolve_edge_voice(voice_id: str) -> str:
    if voice_id and "Neural" in voice_id:
        return voice_id
    return EDGE_VOICES.get(voice_id, "en-US-AriaNeural")


def _engine_from_voice_id(voice_id: str) -> str:
    if voice_id.startswith("kokoro-"):
        return "kokoro"
    if voice_id.startswith("piper-"):
        return "piper"
    if voice_id.startswith("orpheus-"):
        return "orpheus"
    return "edge"


def _voice_for_engine(voice_id: str, engine: str) -> str:
    if engine == "edge":
        return resolve_edge_voice(voice_id)
    if "-" in voice_id:
        return voice_id.split("-", 1)[1]
    if engine == "kokoro":
        return "af_sky"
    if engine == "piper":
        return "en_US-lessac-medium"
    return "af_sky"


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


async def _synthesise_cpu_engine(text: str, engine: str, voice_id: str) -> dict | JSONResponse:
    try:
        audio = await _tts_router.synthesize(text=text, engine=engine, voice_id=voice_id)
        audio_b64 = base64.b64encode(audio).decode()
        return {
            "audioUrl": f"data:audio/wav;base64,{audio_b64}",
            "voiceId": voice_id,
            "engine": engine,
            "charCount": len(text),
        }
    except Exception as exc:
        logger.exception("%s synthesis failed", engine)
        return JSONResponse({"error": f"{engine} synthesis failed: {exc}"}, status_code=503)


@router.get("/preset-voices")
async def preset_voices():
    return {
        "voices": EDGE_VOICE_LIST + CPU_VOICE_LIST,
        "previewSentence": PREVIEW_SENTENCE,
        "cpuOnly": True,
    }


@router.post("/preview")
async def preview_voice(body: dict):
    voice_id = body.get("voiceId", "preset-aria")
    text = body.get("text", PREVIEW_SENTENCE)
    engine = body.get("engine") or _engine_from_voice_id(voice_id)

    if engine == "edge":
        result = await _synthesise_edge(text, voice_id)
        if not isinstance(result, JSONResponse):
            return result
        fallback = await _synthesise_cpu_engine(text, "kokoro", "af_sky")
        return fallback if not isinstance(fallback, JSONResponse) else result

    cpu_voice = _voice_for_engine(voice_id, engine)
    result = await _synthesise_cpu_engine(text, engine, cpu_voice)
    if not isinstance(result, JSONResponse):
        return result

    fallback = await _synthesise_edge(text, "preset-aria")
    return fallback if not isinstance(fallback, JSONResponse) else result


@router.post("/synthesise")
async def synthesise(body: dict):
    text = body.get("text")
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    voice_id = body.get("voiceId", "preset-aria")
    engine = body.get("engine") or _engine_from_voice_id(voice_id)

    if engine == "edge":
        result = await _synthesise_edge(text, voice_id)
        if not isinstance(result, JSONResponse):
            return result
        fallback = await _synthesise_cpu_engine(text, "kokoro", "af_sky")
        return fallback if not isinstance(fallback, JSONResponse) else result

    cpu_voice = _voice_for_engine(voice_id, engine)
    result = await _synthesise_cpu_engine(text, engine, cpu_voice)
    if not isinstance(result, JSONResponse):
        return result

    fallback = await _synthesise_edge(text, "preset-aria")
    return fallback if not isinstance(fallback, JSONResponse) else result


@router.post("/clone-voice")
async def clone_voice(file: UploadFile | None = File(default=None), audio: UploadFile | None = File(default=None)):
    _ = file or audio
    return JSONResponse(
        {
            "error": "Voice cloning via this endpoint is disabled in CPU-only mode. Use Orpheus service for expressive/clone workflows.",
        },
        status_code=410,
    )


@router.post("/clone-preview")
async def clone_preview(body: dict):
    _ = body
    return JSONResponse(
        {
            "error": "Clone preview is disabled in CPU-only mode. Use Orpheus service for expressive/clone workflows.",
        },
        status_code=410,
    )
