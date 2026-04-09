@echo off
title VoiceFlow — FastAPI Backend (port 8000)
echo ============================================
echo   VoiceFlow — FastAPI Backend
echo ============================================
echo.

cd /d "%~dp0\new_backend\python-backend"

echo Starting FastAPI backend on http://localhost:8000 ...
echo.

"%~dp0.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
