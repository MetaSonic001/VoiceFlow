@echo off
echo VoiceFlow Backend Setup
echo =======================

echo Step 1: Installing NestJS dependencies...
cd nestjs-backend
call npm install
cd ..

echo Step 2: Installing FastAPI dependencies...
cd ingestion-service
call pip install -r requirements.txt
cd ..

echo Step 3: Running database migrations...
cd nestjs-backend
call npx prisma migrate dev --name init
cd ..

echo Setup complete! Now run the applications in separate terminals:
echo.
echo Terminal 1 - NestJS Backend:
echo   cd nestjs-backend ^& npm run start:dev
echo.
echo Terminal 2 - FastAPI Ingestion:
echo   cd ingestion-service ^& python main.py
echo.
echo Infrastructure services are already running in Docker.
pause