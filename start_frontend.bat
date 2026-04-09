@echo off
title VoiceFlow — Django Frontend (port 8090)
echo ============================================
echo   VoiceFlow — Django Frontend
echo ============================================
echo.

cd /d "%~dp0\voiceflow-django"

echo Starting Django frontend on http://localhost:8090 ...
echo.

"%~dp0.venv\Scripts\python.exe" manage.py runserver 8090
