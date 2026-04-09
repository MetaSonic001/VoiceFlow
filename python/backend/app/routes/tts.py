"""
/api/tts routes — Edge TTS (Microsoft) for high-quality text-to-speech.
Chatterbox TTS supported as optional custom voice engine via external service.
"""
import base64
import io
import logging

import edge_tts
import httpx
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

from app.config import settings

router = APIRouter()
logger = logging.getLogger("voiceflow.tts")

PREVIEW_SENTENCE = (
    "Hello! I'm your AI voice assistant. I can help answer questions about your "
    "company, guide customers through your products, and provide real-time support "
    "in a natural, conversational tone. Let me know how you'd like to get started!"
)

# Edge TTS voice catalogue
EDGE_VOICES = {
    "": "en-US-AriaNeural",
    "preset-aria": "en-US-AriaNeural",
    "preset-jenny": "en-US-JennyNeural",
    "preset-guy": "en-US-GuyNeural",
    "preset-davis": "en-US-DavisNeural",
    "preset-sara": "en-US-SaraNeural",
    "preset-tony": "en-US-TonyNeural",
    "preset-nancy": "en-US-NancyNeural",
    "preset-amber": "en-US-AmberNeural",
    "preset-ana": "en-US-AnaNeural",
    "preset-andrew": "en-US-AndrewNeural",
    "preset-brian": "en-US-BrianNeural",
    "preset-emma": "en-US-EmmaNeural",
    "preset-steffan": "en-US-SteffanNeural",
}

VOICE_LIST = [
    {"id": "preset-aria", "name": "Aria", "gender": "Female", "style": "Friendly & warm", "language": "en-US"},
    {"id": "preset-jenny", "name": "Jenny", "gender": "Female", "style": "Professional", "language": "en-US"},
    {"id": "preset-emma", "name": "Emma", "gender": "Female", "style": "Cheerful", "language": "en-US"},
    {"id": "preset-sara", "name": "Sara", "gender": "Female", "style": "Calm & composed", "language": "en-US"},
    {"id": "preset-nancy", "name": "Nancy", "gender": "Female", "style": "Conversational", "language": "en-US"},
    {"id": "preset-amber", "name": "Amber", "gender": "Female", "style": "Casual", "language": "en-US"},
    {"id": "preset-ana", "name": "Ana", "gender": "Female", "style": "Soft & gentle", "language": "en-US"},
    {"id": "preset-guy", "name": "Guy", "gender": "Male", "style": "News anchor", "language": "en-US"},
    {"id": "preset-davis", "name": "Davis", "gender": "Male", "style": "Deep & authoritative", "language": "en-US"},
    {"id": "preset-tony", "name": "Tony", "gender": "Male", "style": "Casual & upbeat", "language": "en-US"},
    {"id": "preset-andrew", "name": "Andrew", "gender": "Male", "style": "Warm & articulate", "language": "en-US"},
    {"id": "preset-brian", "name": "Brian", "gender": "Male", "style": "Confident narrator", "language": "en-US"},
    {"id": "preset-steffan", "name": "Steffan", "gender": "Male", "style": "Smooth & clear", "language": "en-US"},
]


def resolve_edge_voice(voice_id: str) -> str:
    return EDGE_VOICES.get(voice_id, "en-US-AriaNeural")


@router.get("/preset-voices")
async def preset_voices():
    return {"voices": VOICE_LIST, "previewSentence": PREVIEW_SENTENCE}


@router.post("/preview")
async def preview_voice(body: dict):
    """Generate a preview clip of a voice using a standard sample sentence."""
    voice_id = body.get("voiceId", "preset-aria")
    text = body.get("text", PREVIEW_SENTENCE)
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


@router.post("/synthesise")
async def synthesise(body: dict):
    text = body.get("text")
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    voice_id = body.get("voiceId", "")
    use_chatterbox = body.get("engine") == "chatterbox"

    # If customer chose Chatterbox and the service is running, use it
    if use_chatterbox:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.post(
                    f"{settings.TTS_SERVICE_URL}/synthesise",
                    data={"text": text, "voiceId": voice_id},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            logger.info("Chatterbox TTS unavailable, falling back to Edge TTS")

    # Default: Edge TTS
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
            "charCount": len(text),
        }
    except Exception as e:
        logger.exception("Edge TTS synthesis failed")
        return JSONResponse({"error": f"TTS synthesis failed: {e}"}, status_code=500)


@router.post("/clone-voice")
async def clone_voice(file: UploadFile = File(...)):
    """Proxy to Chatterbox TTS for voice cloning (requires external service)."""
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        return JSONResponse({"error": "Audio file is too large (max 20MB)"}, status_code=400)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.TTS_SERVICE_URL}/clone-voice",
                files={"file": (file.filename, content, file.content_type)},
            )
            if resp.status_code == 200:
                return resp.json()
            return JSONResponse({"error": "Chatterbox clone failed"}, status_code=resp.status_code)
    except Exception:
        return JSONResponse(
            {"error": "Voice cloning requires the Chatterbox TTS service (port 8003). It is not currently running."},
            status_code=503,
        )
