@echo off
title VoiceFlow — Stopping All Services
echo ============================================
echo   VoiceFlow — Stopping Everything
echo ============================================
echo.

echo Stopping Docker services...
cd /d "%~dp0\new_backend"
docker compose down
echo.

echo Killing any Python servers on ports 8000 and 8090...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8090 ^| findstr LISTENING') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo All services stopped.
echo.
pause
