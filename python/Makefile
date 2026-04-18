# ═══════════════════════════════════════════════════════════════════
# VoiceFlow — Makefile  (PowerShell-native)
# Run from: python/ directory  →  make all
#
# NEW USER QUICKSTART:
#   1. make init          (one-time: venv + deps + env + docker + migrate)
#   2. make all           (start everything — backend + frontend + docker)
#   3. Open http://localhost:8050
#
# ═══════════════════════════════════════════════════════════════════

SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -Command

# PowerShell executable for Start-Process calls
SHELL_EXE := powershell.exe

VENV   := $(CURDIR)/../.venv
PYTHON := $(VENV)/Scripts/python.exe
UV     := $(VENV)/Scripts/uv.exe

# ─── HELP ─────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@Write-Host ''
	@Write-Host '  VoiceFlow Commands' -ForegroundColor Cyan
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan
	@Write-Host ''
	@Write-Host '  QUICKSTART' -ForegroundColor Yellow
	@Write-Host '    make init              One-time full setup (venv + deps + env + docker + migrate)'
	@Write-Host '    make all               Start everything (Docker + Backend + Frontend)'
	@Write-Host ''
	@Write-Host '  STARTUP' -ForegroundColor Yellow
	@Write-Host '    make docker            Start Docker services only'
	@Write-Host '    make backend           Start FastAPI backend (port 8040, foreground)'
	@Write-Host '    make backend-bg        Start FastAPI backend (new window)'
	@Write-Host '    make frontend          Start Django frontend (port 8050, foreground)'
	@Write-Host '    make frontend-bg       Start Django frontend (new window)'
	@Write-Host ''
	@Write-Host '  STOP / RESTART' -ForegroundColor Yellow
	@Write-Host '    make stop              Stop all services'
	@Write-Host '    make stop-backend      Stop backend only'
	@Write-Host '    make stop-frontend     Stop frontend only'
	@Write-Host '    make stop-docker       Stop Docker containers only'
	@Write-Host '    make restart-backend   Restart backend (stop + start in new window)'
	@Write-Host '    make restart-frontend  Restart frontend (stop + start in new window)'
	@Write-Host ''
	@Write-Host '  SETUP' -ForegroundColor Yellow
	@Write-Host '    make venv              Create Python virtual environment'
	@Write-Host '    make install           Install all Python dependencies'
	@Write-Host '    make lock              Generate/update uv.lock from pyproject.toml'
	@Write-Host '    make env               Create .env from .env.example'
	@Write-Host '    make migrate           Run Django makemigrations + migrate'
	@Write-Host '    make makemigrations    Run Django makemigrations only'
	@Write-Host '    make superuser         Create Django admin superuser'
	@Write-Host '    make seed              Seed default agent templates'
	@Write-Host ''
	@Write-Host '  DATABASE' -ForegroundColor Yellow
	@Write-Host '    make db-shell          Open psql shell'
	@Write-Host '    make db-tables         List all database tables'
	@Write-Host '    make db-agents         List agents in database'
	@Write-Host ''
	@Write-Host '  TESTING' -ForegroundColor Yellow
	@Write-Host '    make test              Quick health check (backend + frontend)'
	@Write-Host '    make test-endpoints    Comprehensive API endpoint test'
	@Write-Host '    make test-rag          Document upload + RAG test'
	@Write-Host ''
	@Write-Host '  UTILS' -ForegroundColor Yellow
	@Write-Host '    make status            Show status of all services'
	@Write-Host '    make logs              Tail Docker logs'
	@Write-Host '    make clean             Remove __pycache__ and .pyc files'
	@Write-Host '    make reset             Stop everything + clean'
	@Write-Host '    make demo-reset        Clear app data for a fresh demo (keeps images/venv)'
	@Write-Host '    make nuke              Stop everything + wipe all data + rebuild fresh'
	@Write-Host ''

# ─── FIRST-TIME INIT ─────────────────────────────────────────────

.PHONY: init
init: venv install env docker wait migrate seed ## One-time full setup
	@Write-Host ''
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan
	@Write-Host '  Setup complete!' -ForegroundColor Green
	@Write-Host ''
	@Write-Host '  Run "make all" to start all services, then open:'
	@Write-Host '    Frontend : http://localhost:8050'
	@Write-Host '    Backend  : http://localhost:8040/health'
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan

.PHONY: venv
venv: ## Create Python virtual environment + install uv
	@if (-not (Test-Path '$(VENV)/Scripts/activate.bat')) { Write-Host 'Creating virtual environment...' -ForegroundColor Yellow; python -m venv '$(VENV)'; & '$(PYTHON)' -m pip install --quiet --upgrade pip uv; Write-Host 'Virtual environment created at $(VENV)' -ForegroundColor Green } else { Write-Host 'Virtual environment already exists at $(VENV)' -ForegroundColor Gray }

.PHONY: env
env: ## Create .env from .env.example if missing
	@if (-not (Test-Path '.env')) { if (Test-Path '.env.example') { Copy-Item '.env.example' '.env'; Write-Host 'Created .env from .env.example — edit it with your GROQ_API_KEY' -ForegroundColor Yellow } else { Write-Host '.env.example not found — create .env manually.' -ForegroundColor Red } } else { Write-Host '.env already exists — skipping.' -ForegroundColor Gray }

# ─── START SERVICES ───────────────────────────────────────────────

.PHONY: all
all: docker wait backend-bg frontend-bg ## Start everything
	@Write-Host ''
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan
	@Write-Host '  All services started!' -ForegroundColor Green
	@Write-Host ''
	@Write-Host '  Frontend : http://localhost:8050'
	@Write-Host '  Backend  : http://localhost:8040'
	@Write-Host '  Postgres : localhost:8010'
	@Write-Host '  MinIO    : localhost:9020'
	@Write-Host '  ChromaDB : localhost:8030'
	@Write-Host '  Redis    : localhost:8020'
	@Write-Host '  ═══════════════════════════════════════════════════' -ForegroundColor Cyan

.PHONY: docker
docker: ## Start Docker services (Postgres, MinIO, ChromaDB, Redis)
	docker compose up -d postgres minio chroma redis
	@Write-Host 'Docker services started.' -ForegroundColor Green

.PHONY: wait
wait:
	@Write-Host 'Waiting for services to be ready...' -ForegroundColor Yellow
	@Start-Sleep -Seconds 10

.PHONY: backend
backend: ## Start FastAPI backend (foreground, port 8040)
	cd backend; & '$(PYTHON)' -m uvicorn main:app --host 127.0.0.1 --port 8040 --reload

.PHONY: backend-bg
backend-bg: ## Start FastAPI backend (background window)
	@Start-Process $(SHELL_EXE) -ArgumentList '-NoExit', '-Command', "& '$(VENV)/Scripts/Activate.ps1'; Set-Location '$(CURDIR)/backend'; & '$(PYTHON)' -m uvicorn main:app --host 127.0.0.1 --port 8040 --reload"
	@Write-Host 'Backend started in new window (port 8040)' -ForegroundColor Green

.PHONY: frontend
frontend: ## Start Django frontend (foreground, port 8050)
	cd frontend; & '$(PYTHON)' manage.py runserver 8050

.PHONY: frontend-bg
frontend-bg: ## Start Django frontend (background window)
	@Start-Process $(SHELL_EXE) -ArgumentList '-NoExit', '-Command', "& '$(VENV)/Scripts/Activate.ps1'; Set-Location '$(CURDIR)/frontend'; & '$(PYTHON)' manage.py runserver 8050"
	@Write-Host 'Frontend started in new window (port 8050)' -ForegroundColor Green

# ─── STOP / RESTART ───────────────────────────────────────────────

.PHONY: stop
stop: stop-docker stop-backend stop-frontend ## Stop all services
	@Write-Host 'All services stopped.' -ForegroundColor Green

.PHONY: stop-backend
stop-backend: ## Stop backend only
	@Write-Host 'Stopping backend...' -ForegroundColor Yellow
	@Get-Process -Name 'python' -ErrorAction SilentlyContinue | Where-Object { $$_.CommandLine -match 'uvicorn' } | Stop-Process -Force -ErrorAction SilentlyContinue
	@Start-Sleep -Seconds 1
	@Write-Host 'Backend stopped.' -ForegroundColor Green

.PHONY: stop-frontend
stop-frontend: ## Stop frontend only
	@Write-Host 'Stopping frontend...' -ForegroundColor Yellow
	@Get-Process -Name 'python' -ErrorAction SilentlyContinue | Where-Object { $$_.CommandLine -match 'runserver' } | Stop-Process -Force -ErrorAction SilentlyContinue
	@Start-Sleep -Seconds 1
	@Write-Host 'Frontend stopped.' -ForegroundColor Green

.PHONY: stop-docker
stop-docker: ## Stop Docker containers
	docker compose down

.PHONY: restart-backend
restart-backend: stop-backend backend-bg ## Restart backend
	@Write-Host 'Backend restarted.' -ForegroundColor Green

.PHONY: restart-frontend
restart-frontend: stop-frontend frontend-bg ## Restart frontend
	@Write-Host 'Frontend restarted.' -ForegroundColor Green

# ─── SETUP ────────────────────────────────────────────────────────

.PHONY: install
install: install-deps ## Install all Python dependencies from pyproject.toml

.PHONY: install-deps
install-deps: ## Sync Python dependencies from pyproject.toml via uv
	@if (Test-Path '$(UV)') { & '$(UV)' sync } else { & '$(PYTHON)' -m pip install --upgrade pip uv; & '$(VENV)/Scripts/uv.exe' sync }

.PHONY: lock
lock: ## Resolve and write uv.lock from pyproject.toml
	@if (Test-Path '$(UV)') { & '$(UV)' lock } else { & '$(PYTHON)' -m pip install --upgrade pip uv; & '$(VENV)/Scripts/uv.exe' lock }

.PHONY: migrate
migrate: ## Run Django makemigrations + migrate
	cd frontend; & '$(PYTHON)' manage.py makemigrations core
	cd frontend; & '$(PYTHON)' manage.py migrate

.PHONY: makemigrations
makemigrations: ## Run Django makemigrations only
	cd frontend; & '$(PYTHON)' manage.py makemigrations core

.PHONY: superuser
superuser: ## Create Django admin superuser
	cd frontend; & '$(PYTHON)' manage.py createsuperuser

.PHONY: seed
seed: ## Seed default agent templates
	@Write-Host 'Seeding default templates...' -ForegroundColor Yellow
	@Push-Location backend; & '$(PYTHON)' -c "from main import seed_defaults; import asyncio; asyncio.run(seed_defaults())"; Pop-Location

.PHONY: setup
setup: install docker wait migrate ## Setup without venv creation
	@Write-Host ''
	@Write-Host '  Setup complete! Run "make all" to start.' -ForegroundColor Green

# ─── DATABASE ─────────────────────────────────────────────────────

.PHONY: db-shell
db-shell: ## Open psql shell
	docker compose exec postgres psql -U vf_admin -d voiceflow_prod

.PHONY: db-tables
db-tables: ## List database tables
	docker compose exec postgres psql -U vf_admin -d voiceflow_prod -c '\dt'

.PHONY: db-agents
db-agents: ## Show agents in database
	docker compose exec postgres psql -U vf_admin -d voiceflow_prod -c 'SELECT id, name, status, "tenantId" FROM agents ORDER BY "createdAt" DESC;'

# ─── TESTING ──────────────────────────────────────────────────────

.PHONY: test
test: ## Quick health check — verify backend + frontend are running
	@try { & '$(PYTHON)' -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8040/health'); print('Backend  OK:', r.status)" } catch { Write-Host 'Backend  FAILED — not reachable on :8040' -ForegroundColor Red }
	@try { & '$(PYTHON)' -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8050/'); print('Frontend OK:', r.status)" } catch { Write-Host 'Frontend FAILED — not reachable on :8050' -ForegroundColor Red }

.PHONY: test-endpoints
test-endpoints: ## Run comprehensive API endpoint validation
	cd ..; & '$(PYTHON)' test_all_endpoints.py

.PHONY: test-rag
test-rag: ## Run document upload + RAG retrieval E2E test
	cd ..; & '$(PYTHON)' test_rag_pipeline.py

# ─── UTILS ────────────────────────────────────────────────────────

.PHONY: status
status: ## Show status of all services
	@Write-Host ''
	@Write-Host '  Docker containers:' -ForegroundColor Yellow
	@try { docker compose ps } catch { Write-Host '  (Docker not running)' -ForegroundColor Gray }
	@Write-Host ''
	@Write-Host '  Port 8040 (Backend):' -ForegroundColor Yellow
	@$$b = netstat -aon | Select-String ':8040.*LISTENING'; if ($$b) { $$b | ForEach-Object { Write-Host "    $$_" } } else { Write-Host '    Not running' -ForegroundColor Gray }
	@Write-Host '  Port 8050 (Frontend):' -ForegroundColor Yellow
	@$$f = netstat -aon | Select-String ':8050.*LISTENING'; if ($$f) { $$f | ForEach-Object { Write-Host "    $$_" } } else { Write-Host '    Not running' -ForegroundColor Gray }
	@Write-Host ''

.PHONY: logs
logs: ## Tail Docker logs
	docker compose logs -f

.PHONY: logs-postgres
logs-postgres: ## Tail Postgres logs
	docker compose logs -f postgres

.PHONY: clean
clean: ## Remove __pycache__ and .pyc files
	@Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
	@Get-ChildItem -Path . -Recurse -Filter '*.pyc' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
	@Write-Host 'Cleaned.' -ForegroundColor Green

.PHONY: reset
reset: stop clean ## Stop everything + clean

.PHONY: demo-reset
demo-reset: ## Clear app data for a clean demo without full nuke
	@Write-Host 'Preparing clean demo state...' -ForegroundColor Yellow
	@Write-Host 'Stopping backend/frontend processes...' -ForegroundColor Yellow
	@Get-Process -Name 'python' -ErrorAction SilentlyContinue | Where-Object { $$_.Path -like '*VoiceFlow*' -and ($$_.CommandLine -match 'uvicorn|runserver') } | Stop-Process -Force -ErrorAction SilentlyContinue
	@Write-Host 'Ensuring Docker data services are running...' -ForegroundColor Yellow
	@docker compose up -d postgres redis chroma minio
	@Write-Host 'Flushing PostgreSQL data (preserves schema + migrations)...' -ForegroundColor Yellow
	@Push-Location frontend; & '$(PYTHON)' manage.py flush --no-input; Pop-Location
	@Write-Host 'Flushing Redis...' -ForegroundColor Yellow
	@docker compose exec -T redis redis-cli FLUSHALL > $$null
	@Write-Host 'Clearing ChromaDB persisted vectors...' -ForegroundColor Yellow
	@docker compose exec -T chroma sh -c "rm -rf /chroma/chroma/*"
	@Write-Host 'Clearing MinIO object data...' -ForegroundColor Yellow
	@docker compose exec -T minio sh -c "rm -rf /data/*"
	@Write-Host 'Re-seeding default templates...' -ForegroundColor Yellow
	@Push-Location backend; & '$(PYTHON)' -c "from main import seed_defaults; import asyncio; asyncio.run(seed_defaults())"; Pop-Location
	@Write-Host ''
	@Write-Host '=== DEMO RESET COMPLETE ===' -ForegroundColor Green
	@Write-Host 'Data cleared. Start app with: make all' -ForegroundColor Cyan

.PHONY: nuke
nuke: ## Stop everything + wipe ALL data (Postgres, Redis, ChromaDB, MinIO) + rebuild fresh
	@Write-Host 'NUKING everything — stopping services...' -ForegroundColor Red
	@Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $$_.Path -like '*VoiceFlow*' } | Stop-Process -Force -ErrorAction SilentlyContinue
	@Start-Sleep -Seconds 2
	@Write-Host 'Removing Docker containers + volumes...' -ForegroundColor Yellow
	@docker compose down -v --remove-orphans 2>$$null; $$true
	@Write-Host 'Cleaning pycache...' -ForegroundColor Yellow
	@Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
	@Get-ChildItem -Path . -Recurse -Filter '*.pyc' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
	@Write-Host 'Starting fresh Docker services...' -ForegroundColor Yellow
	@docker compose up -d
	@Write-Host 'Waiting for Postgres to be ready...' -ForegroundColor Yellow
	@$$attempt=0; while ($$attempt -lt 15) { try { docker compose exec -T postgres pg_isready -U vf_admin -d voiceflow_prod 2>$$null; if ($$LASTEXITCODE -eq 0) { break }; } catch {}; Start-Sleep -Seconds 2; $$attempt++ }
	@Write-Host 'Running migrations...' -ForegroundColor Yellow
	@& "$$((Get-Item ..).FullName)\.venv\Scripts\python.exe" frontend/manage.py migrate --no-input 2>$$null
	@Write-Host '' -ForegroundColor Green
	@Write-Host '=== NUKE COMPLETE ===' -ForegroundColor Green
	@Write-Host 'All data wiped. Docker services running fresh.' -ForegroundColor Green
	@Write-Host 'Run "make all" to start backend + frontend.' -ForegroundColor Cyan
