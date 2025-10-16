@echo off
echo Starting VoiceFlow Backend Services...

cd /d "%~dp0"

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found. Please copy .env.example to .env and configure your API keys.
    echo Required: CLERK_SECRET_KEY, GROQ_API_KEY
    pause
    exit /b 1
)

echo Building and starting all services with Docker Compose...
docker-compose up -d --build

echo Waiting for services to be healthy...
timeout /t 15 /nobreak > nul

echo.
echo Service Status:
docker-compose ps

echo.
echo Useful URLs:
echo - Express Backend API: http://localhost:8000
echo - Ingestion Service: http://localhost:8001
echo - MinIO Console: http://localhost:9001 (admin/minioadmin)
echo - ChromaDB: http://localhost:8002
echo - PostgreSQL: localhost:5433 (vf_admin/vf_secure_2025!)
echo - Redis: localhost:6379
echo.
echo Frontend can be started separately with:
echo cd ../voiceflow-ai-platform ^(1^)
echo npm run dev
echo.
echo To view logs: docker-compose logs -f [service-name]
echo To stop all services: docker-compose down
echo To restart a service: docker-compose restart [service-name]
echo.
pause