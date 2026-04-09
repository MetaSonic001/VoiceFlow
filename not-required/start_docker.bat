@echo off
title VoiceFlow — Docker Services
echo ============================================
echo   VoiceFlow — Starting Docker Services
echo ============================================
echo.

cd /d "%~dp0\new_backend"

echo Starting Postgres, MinIO, ChromaDB, Redis...
echo (TTS service excluded by default — needs NVIDIA GPU)
echo.

docker compose up -d postgres minio chroma redis

echo.
echo Waiting for services to be healthy...
timeout /t 10 /nobreak > nul

docker compose ps

echo.
echo Docker services:
echo   Postgres   : localhost:5433
echo   MinIO      : localhost:9000  (console: localhost:9001)
echo   ChromaDB   : localhost:8002
echo   Redis      : localhost:6379
echo.
echo To also start TTS service (requires NVIDIA GPU):
echo   docker compose up -d tts-service
echo.
pause
