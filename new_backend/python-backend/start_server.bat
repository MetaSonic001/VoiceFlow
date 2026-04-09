@echo off
cd /d "%~dp0"
"c:\Users\Z0058J5C\Personal Project\VoiceFlow\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
