"""
Chatterbox Turbo TTS Microservice
──────────────────────────────────
A FastAPI service that wraps the Chatterbox Turbo 350M model for:
  • Real-time speech synthesis with preset or cloned voices
  • Voice cloning from a short audio reference
  • Caching generated audio in MinIO / S3

Environment variables:
  MINIO_ENDPOINT   – e.g. minio:9000
  MINIO_ACCESS_KEY – default minioadmin
  MINIO_SECRET_KEY – default minioadmin
  MINIO_BUCKET     – default voiceflow-tts
  DEVICE           – cuda | cpu  (default: cuda if available)
"""

import os
import io
import uuid
import hashlib
import tempfile
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import torch
import torchaudio as ta
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydub import AudioSegment
import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tts-service")

# ─── Global state (populated at startup) ──────────────────────────────────────
model = None  # ChatterboxTurboTTS — loaded once
s3 = None     # boto3 S3 client (MinIO-compatible)
BUCKET = os.getenv("MINIO_BUCKET", "voiceflow-tts")
DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")

# ─── Preset voice definitions ─────────────────────────────────────────────────
# Each preset ships a short reference WAV inside the container at /app/presets/.
# If the file doesn't exist we generate a placeholder at first startup.
PRESET_VOICES = [
    {
        "id": "preset-aria",
        "name": "Aria",
        "description": "Warm, professional female voice. Clear enunciation, neutral accent.",
        "ref_file": "aria.wav",
    },
    {
        "id": "preset-raj",
        "name": "Raj",
        "description": "Confident male voice with a slight Indian English accent. Great for support agents.",
        "ref_file": "raj.wav",
    },
    {
        "id": "preset-emma",
        "name": "Emma",
        "description": "Friendly, energetic female voice. Upbeat and approachable for sales.",
        "ref_file": "emma.wav",
    },
    {
        "id": "preset-james",
        "name": "James",
        "description": "Mature, authoritative male voice. Trustworthy for finance and legal.",
        "ref_file": "james.wav",
    },
    {
        "id": "preset-priya",
        "name": "Priya",
        "description": "Soft-spoken female voice, empathetic tone. Ideal for healthcare and HR.",
        "ref_file": "priya.wav",
    },
]

PRESETS_DIR = Path("/app/presets")


# ─── Helper: MinIO / S3 ──────────────────────────────────────────────────────

def get_s3_client():
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    scheme = "https" if os.getenv("MINIO_USE_SSL", "false").lower() == "true" else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{scheme}://{endpoint}",
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket(client):
    try:
        client.head_bucket(Bucket=BUCKET)
    except ClientError:
        client.create_bucket(Bucket=BUCKET)
        logger.info(f"Created MinIO bucket: {BUCKET}")


def object_exists(key: str) -> bool:
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except ClientError:
        return False


def upload_bytes(key: str, data: bytes, content_type: str = "audio/wav"):
    s3.put_object(Bucket=BUCKET, Key=key, Body=data, ContentType=content_type)


def presigned_url(key: str, expires: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=expires,
    )


def download_to_tempfile(key: str, suffix: str = ".wav") -> str:
    """Download an S3 object to a temp file and return the path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    s3.download_fileobj(Bucket=BUCKET, Key=key, Fileobj=tmp)
    tmp.close()
    return tmp.name


# ─── Helper: audio cache key ─────────────────────────────────────────────────

def cache_key(text: str, voice_id: str) -> str:
    h = hashlib.sha256(f"{voice_id}::{text}".encode()).hexdigest()[:24]
    return f"tts-cache/{h}.wav"


# ─── Helper: synthesise with model ───────────────────────────────────────────

def synthesise_audio(text: str, ref_path: str | None = None) -> bytes:
    """Run Chatterbox Turbo and return WAV bytes."""
    kwargs = {"text": text}
    if ref_path:
        kwargs["audio_prompt_path"] = ref_path
    wav_tensor = model.generate(**kwargs)

    buf = io.BytesIO()
    ta.save(buf, wav_tensor, model.sr, format="wav")
    buf.seek(0)
    return buf.read()


def generate_preset_samples():
    """At startup, generate short sample clips for each preset that doesn't
    already have one in MinIO — used as preview audio in the frontend."""
    sample_text = "Hello! I'm your AI assistant. How can I help you today?"
    for preset in PRESET_VOICES:
        sample_key = f"voice-samples/{preset['id']}.wav"
        if object_exists(sample_key):
            continue
        # Synthesise with default voice (no ref) — gives each preset a unique clip
        # once real reference WAVs are provided in /app/presets/ they'll be used
        ref_path = PRESETS_DIR / preset["ref_file"]
        ref = str(ref_path) if ref_path.exists() else None
        try:
            wav_bytes = synthesise_audio(sample_text, ref)
            upload_bytes(sample_key, wav_bytes)
            logger.info(f"Generated sample for {preset['id']}")
        except Exception as e:
            logger.warning(f"Could not generate sample for {preset['id']}: {e}")


# ─── Lifespan: load model + init S3 ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, s3

    logger.info(f"Loading Chatterbox Turbo model on device={DEVICE} …")
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    model = ChatterboxTurboTTS.from_pretrained(device=DEVICE)
    logger.info("Model loaded successfully.")

    s3 = get_s3_client()
    ensure_bucket(s3)

    # Make presets directory if it doesn't exist (for local dev)
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate preset sample clips in the background
    try:
        generate_preset_samples()
    except Exception as e:
        logger.warning(f"Preset sample generation failed (non-fatal): {e}")

    yield  # app runs

    logger.info("Shutting down TTS service")


# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="VoiceFlow TTS Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── GET /health ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "device": DEVICE,
    }


# ─── GET /preset-voices ──────────────────────────────────────────────────────

@app.get("/preset-voices")
def preset_voices():
    """Return the list of built-in preset voices with sample URLs."""
    result = []
    for p in PRESET_VOICES:
        sample_key = f"voice-samples/{p['id']}.wav"
        sample_url = presigned_url(sample_key) if object_exists(sample_key) else None
        result.append({
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "sampleUrl": sample_url,
        })
    return {"voices": result}


# ─── POST /synthesise ────────────────────────────────────────────────────────

@app.post("/synthesise")
async def synthesise(
    text: str = Form(...),
    voiceId: str = Form("preset-aria"),
    agentId: str = Form(None),
):
    """
    Synthesise speech from text using a preset or cloned voice.
    Returns a presigned URL to the generated WAV file.
    """
    if not text or not text.strip():
        raise HTTPException(400, "text is required")

    # Check cache first
    ck = cache_key(text, voiceId)
    if object_exists(ck):
        return {"audioUrl": presigned_url(ck), "cached": True}

    # Resolve voice reference audio
    ref_path: str | None = None
    tmp_ref: str | None = None

    if voiceId.startswith("preset-"):
        # Find preset
        preset = next((p for p in PRESET_VOICES if p["id"] == voiceId), None)
        if not preset:
            raise HTTPException(400, f"Unknown preset voice: {voiceId}")
        local_ref = PRESETS_DIR / preset["ref_file"]
        if local_ref.exists():
            ref_path = str(local_ref)
        # else: no ref → model uses its default voice

    elif voiceId.startswith("clone-"):
        # Load cloned voice reference from MinIO
        clone_key = f"voice-profiles/{voiceId}.wav"
        if not object_exists(clone_key):
            raise HTTPException(404, f"Cloned voice not found: {voiceId}")
        tmp_ref = download_to_tempfile(clone_key)
        ref_path = tmp_ref

    else:
        raise HTTPException(400, "voiceId must start with 'preset-' or 'clone-'")

    try:
        wav_bytes = synthesise_audio(text, ref_path)
    finally:
        # Clean up temp file if we downloaded one
        if tmp_ref and os.path.exists(tmp_ref):
            os.unlink(tmp_ref)

    # Upload to cache and return presigned URL
    upload_bytes(ck, wav_bytes)
    return {"audioUrl": presigned_url(ck), "cached": False}


# ─── POST /clone-voice ───────────────────────────────────────────────────────

@app.post("/clone-voice")
async def clone_voice(file: UploadFile = File(...)):
    """
    Accept a WAV/MP3 file (5–60s), store it as a voice profile in MinIO,
    and return a voiceId that can be used with /synthesise.
    """
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(400, "File must be an audio file (WAV or MP3)")

    raw_bytes = await file.read()
    if len(raw_bytes) < 1000:
        raise HTTPException(400, "Audio file is too small")
    if len(raw_bytes) > 100 * 1024 * 1024:
        raise HTTPException(400, "Audio file is too large (max 100MB)")

    # Convert to WAV (mono, 16kHz) to normalise input
    try:
        audio = AudioSegment.from_file(io.BytesIO(raw_bytes))
    except Exception:
        raise HTTPException(400, "Could not decode audio file. Please upload WAV or MP3.")

    duration_secs = len(audio) / 1000.0
    if duration_secs < 5:
        raise HTTPException(400, f"Audio too short ({duration_secs:.1f}s). Minimum 5 seconds.")
    if duration_secs > 60:
        raise HTTPException(400, f"Audio too long ({duration_secs:.1f}s). Maximum 60 seconds.")

    # Convert to mono WAV at original sample rate (Chatterbox handles resampling)
    audio = audio.set_channels(1)
    wav_buf = io.BytesIO()
    audio.export(wav_buf, format="wav")
    wav_bytes = wav_buf.getvalue()

    # Store reference audio in MinIO
    voice_uuid = str(uuid.uuid4())[:12]
    voice_id = f"clone-{voice_uuid}"
    profile_key = f"voice-profiles/{voice_id}.wav"
    upload_bytes(profile_key, wav_bytes)

    # Quick validation: try a short synthesis to make sure the reference works
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.write(wav_bytes)
    tmp.close()
    try:
        test_wav = synthesise_audio("Hello, this is a test.", tmp.name)
        # Upload the test clip so the frontend can play it immediately
        test_key = f"voice-samples/{voice_id}-test.wav"
        upload_bytes(test_key, test_wav)
        test_url = presigned_url(test_key)
    except Exception as e:
        # Remove the profile if synthesis failed
        try:
            s3.delete_object(Bucket=BUCKET, Key=profile_key)
        except Exception:
            pass
        raise HTTPException(500, f"Voice cloning failed: {e}")
    finally:
        os.unlink(tmp.name)

    return {
        "voiceId": voice_id,
        "testAudioUrl": test_url,
    }
