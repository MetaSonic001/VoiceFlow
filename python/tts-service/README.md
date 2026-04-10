# Chatterbox Turbo TTS Service

A self-hosted, zero-cost TTS microservice powered by [Chatterbox Turbo](https://github.com/resemble-ai/chatterbox) (350M params, MIT licensed).

## Features

- **Real-time synthesis** — under 300ms for short sentences on GPU
- **5 preset voices** — ready to use out of the box
- **Voice cloning** — upload 5-60s of audio to create a custom voice
- **Audio caching** — MinIO-backed cache avoids re-generating the same text
- **Paralinguistic tags** — embed `[laugh]`, `[chuckle]`, `[sigh]` in text

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/preset-voices` | List built-in voices with sample audio URLs |
| POST | `/synthesise` | Generate speech (form: text, voiceId, agentId?) |
| POST | `/clone-voice` | Upload audio to create a cloned voice profile |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO / S3 endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | S3 access key |
| `MINIO_SECRET_KEY` | `minioadmin` | S3 secret key |
| `MINIO_BUCKET` | `voiceflow-tts` | Bucket for cache and voice profiles |
| `DEVICE` | `cuda` if available | `cuda` or `cpu` |

## Running Locally

```bash
pip install -r requirements.txt
MINIO_ENDPOINT=localhost:9020 uvicorn main:app --port 8060
```

## Docker

```bash
docker build -t voiceflow-tts .
docker run -p 8060:8060 \
  -e MINIO_ENDPOINT=minio:9000 \
  --gpus all \
  voiceflow-tts
```
