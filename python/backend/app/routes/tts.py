"""
/api/tts routes — mirrors Express src/routes/tts.ts
Proxy to TTS microservice.
"""
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import JSONResponse
import httpx

from app.config import settings

router = APIRouter()


@router.get("/preset-voices")
async def preset_voices():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.TTS_SERVICE_URL}/preset-voices")
            return resp.json()
    except Exception:
        return JSONResponse({"error": "TTS service unavailable"}, status_code=502)


@router.post("/synthesise")
async def synthesise(body: dict):
    text = body.get("text")
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    voice_id = body.get("voiceId", "preset-aria")
    agent_id = body.get("agentId")

    try:
        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.post(
                f"{settings.TTS_SERVICE_URL}/synthesise",
                data={"text": text, "voiceId": voice_id, **({"agentId": agent_id} if agent_id else {})},
            )
            return resp.json()
    except Exception:
        return JSONResponse({"error": "TTS synthesis failed"}, status_code=502)


@router.post("/clone-voice")
async def clone_voice(file: UploadFile = File(...)):
    if not file:
        return JSONResponse({"error": "No audio file provided"}, status_code=400)

    content = await file.read()
    if len(content) < 50 * 1024:
        return JSONResponse({"error": "Audio file is too short"}, status_code=400)
    if len(content) > 20 * 1024 * 1024:
        return JSONResponse({"error": "Audio file is too large"}, status_code=400)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.TTS_SERVICE_URL}/clone-voice",
                files={"file": (file.filename, content, file.content_type)},
            )
            result = resp.json()
            result["referenceAudioGuidelines"] = {
                "idealDuration": "10-60 seconds",
                "idealFormat": "WAV or MP3 (128+ kbps)",
                "bestPractices": [
                    "Record in a quiet room with minimal background noise.",
                    "Speak naturally at a conversational pace.",
                    "Use a headset mic or phone held close to your mouth.",
                    "Read a paragraph of text rather than repeating one phrase.",
                ],
            }
            return result
    except Exception:
        return JSONResponse({"error": "Voice cloning failed"}, status_code=502)
