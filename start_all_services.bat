@echo off
title VoiceFlow — Starting All Services
echo ============================================
echo   VoiceFlow — Starting Everything
echo ============================================
echo.
echo This will start:
echo   1. Docker services (Postgres, MinIO, ChromaDB, Redis)
echo   2. FastAPI Backend  (port 8000)
echo   3. Django Frontend  (port 8090)
echo.

REM --- Step 1: Docker ---
echo [1/3] Starting Docker services...
cd /d "%~dp0\new_backend"
docker compose up -d postgres minio chroma redis
echo      Docker services started.
echo.

echo Waiting for Postgres to be ready...
timeout /t 8 /nobreak > nul
echo.

REM --- Step 2: Backend ---
echo [2/3] Starting FastAPI Backend...
start "VoiceFlow Backend" cmd /k "cd /d "%~dp0\new_backend\python-backend" && "%~dp0.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 /nobreak > nul
echo      Backend starting on http://localhost:8000
echo.

REM --- Step 3: Frontend ---
echo [3/3] Starting Django Frontend...
start "VoiceFlow Frontend" cmd /k "cd /d "%~dp0\voiceflow-django" && "%~dp0.venv\Scripts\python.exe" manage.py runserver 8090"
timeout /t 2 /nobreak > nul
echo      Frontend starting on http://localhost:8090
echo.

echo ============================================
echo   All services started!
echo ============================================
echo.
echo   Frontend : http://localhost:8090
echo   Backend  : http://localhost:8000
echo   Postgres : localhost:5433
echo   MinIO    : localhost:9001
echo   ChromaDB : localhost:8002
echo   Redis    : localhost:6379
echo.
echo   To stop Docker: cd new_backend ^& docker compose down
echo   To stop Backend/Frontend: close their terminal windows
echo.
pause
