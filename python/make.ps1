<#
.SYNOPSIS
  VoiceFlow — PowerShell build/run helper (replaces Makefile)
  Run from: python/ directory

.DESCRIPTION
  NEW USER QUICKSTART:
    1. .\make.ps1 init        (one-time: venv + deps + env + docker + migrate)
    2. .\make.ps1 all         (start everything)
    3. Open http://localhost:8050

.EXAMPLE
  .\make.ps1 all
  .\make.ps1 backend
  .\make.ps1 stop
#>

param(
    [Parameter(Position = 0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$VENV = Join-Path (Split-Path $PSScriptRoot) ".venv"
$PYTHON = Join-Path $VENV "Scripts\python.exe"
$UV = Join-Path $VENV "Scripts\uv.exe"
$BACKEND = Join-Path $PSScriptRoot "backend"
$FRONTEND = Join-Path $PSScriptRoot "frontend"

function Write-Banner($lines) {
    Write-Host ""
    Write-Host "  ═══════════════════════════════════════════════════" -ForegroundColor Cyan
    foreach ($l in $lines) { Write-Host "  $l" -ForegroundColor White }
    Write-Host "  ═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

# ─── HELP ─────────────────────────────────────────────────────────

function Invoke-Help {
    Write-Host ""
    Write-Host "  VoiceFlow Commands" -ForegroundColor Cyan
    Write-Host "  ═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  QUICKSTART" -ForegroundColor Yellow
    Write-Host "    .\make.ps1 init           One-time full setup"
    Write-Host "    .\make.ps1 all            Start everything (Docker + Backend + Frontend)"
    Write-Host ""
    Write-Host "  STARTUP" -ForegroundColor Yellow
    Write-Host "    .\make.ps1 all            Start everything"
    Write-Host "    .\make.ps1 docker         Start Docker services only"
    Write-Host "    .\make.ps1 backend        Start FastAPI backend (port 8040, foreground)"
    Write-Host "    .\make.ps1 frontend       Start Django frontend (port 8050, foreground)"
    Write-Host ""
    Write-Host "  STOP / RESTART" -ForegroundColor Yellow
    Write-Host "    .\make.ps1 stop              Stop all services"
    Write-Host "    .\make.ps1 stop-backend      Stop backend only"
    Write-Host "    .\make.ps1 stop-frontend     Stop frontend only"
    Write-Host "    .\make.ps1 stop-docker       Stop Docker containers only"
    Write-Host "    .\make.ps1 restart-backend   Restart backend (stop + start in new window)"
    Write-Host "    .\make.ps1 restart-frontend  Restart frontend (stop + start in new window)"
    Write-Host ""
    Write-Host "  SETUP" -ForegroundColor Yellow
    Write-Host "    .\make.ps1 venv           Create Python virtual environment"
    Write-Host "    .\make.ps1 install        Install all Python dependencies"
    Write-Host "    .\make.ps1 env            Create .env from .env.example"
    Write-Host "    .\make.ps1 migrate           Run Django makemigrations + migrate"
    Write-Host "    .\make.ps1 makemigrations    Run Django makemigrations only"
    Write-Host "    .\make.ps1 superuser      Create Django admin superuser"
    Write-Host ""
    Write-Host "  DATABASE" -ForegroundColor Yellow
    Write-Host "    .\make.ps1 db-shell       Open psql shell"
    Write-Host "    .\make.ps1 db-tables      List all database tables"
    Write-Host "    .\make.ps1 db-agents      List agents in database"
    Write-Host ""
    Write-Host "  TESTING" -ForegroundColor Yellow
    Write-Host "    .\make.ps1 test           Quick health check"
    Write-Host "    .\make.ps1 test-endpoints Comprehensive API test"
    Write-Host "    .\make.ps1 test-rag       Document upload + RAG test"
    Write-Host ""
    Write-Host "  UTILS" -ForegroundColor Yellow
    Write-Host "    .\make.ps1 status         Show status of all services"
    Write-Host "    .\make.ps1 logs           Tail Docker logs"
    Write-Host "    .\make.ps1 clean          Remove __pycache__ and .pyc files"
    Write-Host "    .\make.ps1 seed           Seed demo data"
    Write-Host ""
}

# ─── FIRST-TIME INIT ─────────────────────────────────────────────

function Invoke-Init {
    Invoke-Venv
    Invoke-Install
    Invoke-Env
    Invoke-Docker
    Invoke-Wait
    Invoke-Migrate
    Invoke-Seed
    Write-Banner @(
        "Setup complete!",
        "",
        "Run '.\make.ps1 all' to start all services, then open:",
        "  Frontend : http://localhost:8050",
        "  Backend  : http://localhost:8040/health"
    )
}

function Invoke-Venv {
    if (-not (Test-Path (Join-Path $VENV "Scripts\activate.bat"))) {
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv $VENV
        & $PYTHON -m pip install --quiet --upgrade pip uv
        Write-Host "Virtual environment created at $VENV" -ForegroundColor Green
    } else {
        Write-Host "Virtual environment already exists at $VENV" -ForegroundColor Gray
    }
}

function Invoke-Env {
    $envFile = Join-Path $PSScriptRoot ".env"
    $exampleFile = Join-Path $PSScriptRoot ".env.example"
    if (-not (Test-Path $envFile)) {
        if (Test-Path $exampleFile) {
            Copy-Item $exampleFile $envFile
            Write-Host "Created .env from .env.example — edit it with your GROQ_API_KEY" -ForegroundColor Yellow
        } else {
            Write-Host ".env.example not found — create .env manually." -ForegroundColor Red
        }
    } else {
        Write-Host ".env already exists — skipping." -ForegroundColor Gray
    }
}

# ─── START SERVICES ───────────────────────────────────────────────

function Invoke-All {
    Invoke-Docker
    Invoke-Wait
    Invoke-BackendBg
    Invoke-FrontendBg
    Write-Banner @(
        "All services started!",
        "",
        "Frontend : http://localhost:8050",
        "Backend  : http://localhost:8040",
        "Postgres : localhost:8010",
        "MinIO    : localhost:9020",
        "ChromaDB : localhost:8030",
        "Redis    : localhost:8020"
    )
}

function Invoke-Docker {
    Push-Location $PSScriptRoot
    docker compose up -d postgres minio chroma redis
    Pop-Location
    Write-Host "Docker services started." -ForegroundColor Green
}

function Invoke-DockerAll {
    Push-Location $PSScriptRoot
    docker compose up -d
    Pop-Location
    Write-Host "All Docker services started (including TTS)." -ForegroundColor Green
}

function Invoke-Wait {
    Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

function Invoke-Backend {
    Push-Location $BACKEND
    & $PYTHON -m uvicorn main:app --host 127.0.0.1 --port 8040 --reload
    Pop-Location
}

function Invoke-BackendBg {
    $activate = Join-Path $VENV "Scripts\Activate.ps1"
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "& '$activate'; Set-Location '$BACKEND'; & '$PYTHON' -m uvicorn main:app --host 127.0.0.1 --port 8040 --reload" -WindowStyle Normal
    Write-Host "Backend started in new window (port 8040)" -ForegroundColor Green
}

function Invoke-Frontend {
    Push-Location $FRONTEND
    & $PYTHON manage.py runserver 8050
    Pop-Location
}

function Invoke-FrontendBg {
    $activate = Join-Path $VENV "Scripts\Activate.ps1"
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "& '$activate'; Set-Location '$FRONTEND'; & '$PYTHON' manage.py runserver 8050" -WindowStyle Normal
    Write-Host "Frontend started in new window (port 8050)" -ForegroundColor Green
}

# ─── STOP SERVICES ────────────────────────────────────────────────

function Invoke-Stop {
    Invoke-StopDocker
    Invoke-StopBackend
    Invoke-StopFrontend
    Write-Host "All services stopped." -ForegroundColor Green
}

function Invoke-StopBackend {
    Write-Host "Stopping backend..." -ForegroundColor Yellow
    Get-Process -Name "python" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "uvicorn" } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "Backend stopped." -ForegroundColor Green
}

function Invoke-StopFrontend {
    Write-Host "Stopping frontend..." -ForegroundColor Yellow
    Get-Process -Name "python" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "runserver" } |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "Frontend stopped." -ForegroundColor Green
}

function Invoke-RestartBackend {
    Invoke-StopBackend
    Invoke-BackendBg
    Write-Host "Backend restarted." -ForegroundColor Green
}

function Invoke-RestartFrontend {
    Invoke-StopFrontend
    Invoke-FrontendBg
    Write-Host "Frontend restarted." -ForegroundColor Green
}

function Invoke-StopDocker {
    Push-Location $PSScriptRoot
    docker compose down
    Pop-Location
}

# ─── SETUP ────────────────────────────────────────────────────────

function Invoke-Install {
    if (Test-Path $UV) {
        & $UV pip install -r (Join-Path $PSScriptRoot "requirements.txt")
    } else {
        & $PYTHON -m pip install --upgrade pip uv
        & (Join-Path $VENV "Scripts\uv.exe") pip install -r (Join-Path $PSScriptRoot "requirements.txt")
    }
}

function Invoke-Migrate {
    Push-Location $FRONTEND
    & $PYTHON manage.py makemigrations core
    & $PYTHON manage.py migrate
    Pop-Location
}

function Invoke-Makemigrations {
    Push-Location $FRONTEND
    & $PYTHON manage.py makemigrations core
    Pop-Location
}

function Invoke-Superuser {
    Push-Location $FRONTEND
    & $PYTHON manage.py createsuperuser
    Pop-Location
}

function Invoke-Seed {
    Write-Host "Seeding demo data..." -ForegroundColor Yellow
    try {
        Push-Location $BACKEND
        & $PYTHON -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
        Pop-Location
    } catch {
        Write-Host "  Seed will run automatically on first backend start." -ForegroundColor Gray
    }
}

function Invoke-Setup {
    Invoke-Install
    Invoke-Docker
    Invoke-Wait
    Invoke-Migrate
    Write-Host ""
    Write-Host "  Setup complete! Run '.\make.ps1 all' to start." -ForegroundColor Green
}

# ─── DATABASE ─────────────────────────────────────────────────────

function Invoke-DbShell {
    Push-Location $PSScriptRoot
    docker compose exec postgres psql -U vf_admin -d voiceflow_prod
    Pop-Location
}

function Invoke-DbTables {
    Push-Location $PSScriptRoot
    docker compose exec postgres psql -U vf_admin -d voiceflow_prod -c "\dt"
    Pop-Location
}

function Invoke-DbAgents {
    Push-Location $PSScriptRoot
    docker compose exec postgres psql -U vf_admin -d voiceflow_prod -c 'SELECT id, name, status, "tenantId" FROM agents ORDER BY "createdAt" DESC;'
    Pop-Location
}

# ─── TESTING ──────────────────────────────────────────────────────

function Invoke-Test {
    try {
        & $PYTHON -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8040/health'); print('Backend  OK:', r.status)"
    } catch {
        Write-Host "Backend  FAILED — not reachable on :8040" -ForegroundColor Red
    }
    try {
        & $PYTHON -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8050/'); print('Frontend OK:', r.status)"
    } catch {
        Write-Host "Frontend FAILED — not reachable on :8050" -ForegroundColor Red
    }
}

function Invoke-TestEndpoints {
    & $PYTHON (Join-Path (Split-Path $PSScriptRoot) "test_all_endpoints.py")
}

function Invoke-TestRag {
    & $PYTHON (Join-Path (Split-Path $PSScriptRoot) "test_rag_pipeline.py")
}

# ─── UTILS ────────────────────────────────────────────────────────

function Invoke-Status {
    Write-Host ""
    Write-Host "  Docker containers:" -ForegroundColor Yellow
    Push-Location $PSScriptRoot
    try { docker compose ps } catch { Write-Host "  (Docker not running)" -ForegroundColor Gray }
    Pop-Location
    Write-Host ""
    Write-Host "  Port 8040 (Backend):" -ForegroundColor Yellow
    $b = netstat -aon | Select-String ":8040.*LISTENING"
    if ($b) { $b | ForEach-Object { Write-Host "    $_" } } else { Write-Host "    Not running" -ForegroundColor Gray }
    Write-Host "  Port 8050 (Frontend):" -ForegroundColor Yellow
    $f = netstat -aon | Select-String ":8050.*LISTENING"
    if ($f) { $f | ForEach-Object { Write-Host "    $_" } } else { Write-Host "    Not running" -ForegroundColor Gray }
    Write-Host ""
}

function Invoke-Logs {
    Push-Location $PSScriptRoot
    docker compose logs -f
    Pop-Location
}

function Invoke-Clean {
    Get-ChildItem -Path $PSScriptRoot -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $PSScriptRoot -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
    Write-Host "Cleaned." -ForegroundColor Green
}

function Invoke-Reset {
    Invoke-Stop
    Invoke-Clean
}

# ─── DISPATCH ─────────────────────────────────────────────────────

switch ($Command.ToLower()) {
    "help"           { Invoke-Help }
    "init"           { Invoke-Init }
    "venv"           { Invoke-Venv }
    "env"            { Invoke-Env }
    "all"            { Invoke-All }
    "docker"         { Invoke-Docker }
    "docker-all"     { Invoke-DockerAll }
    "wait"           { Invoke-Wait }
    "backend"        { Invoke-Backend }
    "backend-bg"     { Invoke-BackendBg }
    "frontend"       { Invoke-Frontend }
    "frontend-bg"    { Invoke-FrontendBg }
    "stop"              { Invoke-Stop }
    "stop-backend"      { Invoke-StopBackend }
    "stop-frontend"     { Invoke-StopFrontend }
    "restart-backend"   { Invoke-RestartBackend }
    "restart-frontend"  { Invoke-RestartFrontend }
    "stop-docker"       { Invoke-StopDocker }
    "install"        { Invoke-Install }
    "migrate"           { Invoke-Migrate }
    "makemigrations"    { Invoke-Makemigrations }
    "superuser"      { Invoke-Superuser }
    "seed"           { Invoke-Seed }
    "setup"          { Invoke-Setup }
    "db-shell"       { Invoke-DbShell }
    "db-tables"      { Invoke-DbTables }
    "db-agents"      { Invoke-DbAgents }
    "test"           { Invoke-Test }
    "test-endpoints" { Invoke-TestEndpoints }
    "test-rag"       { Invoke-TestRag }
    "status"         { Invoke-Status }
    "logs"           { Invoke-Logs }
    "clean"          { Invoke-Clean }
    "reset"          { Invoke-Reset }
    default          { Write-Host "Unknown command: $Command. Run '.\make.ps1 help' for options." -ForegroundColor Red }
}
