# ═══════════════════════════════════════════════════════════════════
# VoiceFlow — Makefile
# Run from: python/ directory
#
# NEW USER QUICKSTART:
#   1. make init          (one-time: venv + deps + env + docker + migrate)
#   2. make all           (start everything — backend + frontend + docker)
#   3. Open http://localhost:8090
#
# ═══════════════════════════════════════════════════════════════════

SHELL := cmd.exe
VENV := ..\.venv
PYTHON := $(VENV)\Scripts\python.exe
UV := $(VENV)\Scripts\uv.exe

# ─── Convenience ──────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@echo.
	@echo  VoiceFlow Commands
	@echo  ═══════════════════════════════════════════════════════
	@echo.
	@echo  QUICKSTART (new user)
	@echo    make init           One-time full setup (venv + deps + env + docker + migrate)
	@echo    make all            Start everything (Docker + Backend + Frontend)
	@echo.
	@echo  STARTUP
	@echo    make all            Start everything (Docker + Backend + Frontend)
	@echo    make docker         Start Docker services only
	@echo    make backend        Start FastAPI backend (port 8000)
	@echo    make frontend       Start Django frontend (port 8090)
	@echo.
	@echo  STOP
	@echo    make stop           Stop all services
	@echo    make stop-docker    Stop Docker containers only
	@echo.
	@echo  SETUP
	@echo    make venv           Create Python virtual environment
	@echo    make install        Install all Python dependencies (uv pip)
	@echo    make env            Create .env from .env.example (if missing)
	@echo    make migrate        Run Django migrations
	@echo    make superuser      Create Django admin superuser
	@echo    make setup          Install deps + Docker + migrate (no venv create)
	@echo    make init           Full first-time init (venv + setup)
	@echo.
	@echo  DATABASE
	@echo    make db-shell       Open psql shell
	@echo    make db-tables      List all database tables
	@echo    make db-agents      List agents in database
	@echo.
	@echo  TESTING
	@echo    make test           Quick health check (backend + frontend)
	@echo    make test-endpoints Run comprehensive API endpoint test
	@echo    make test-rag       Run document upload + RAG retrieval test
	@echo.
	@echo  UTILS
	@echo    make status         Show status of all services
	@echo    make logs           Tail Docker logs
	@echo    make clean          Remove __pycache__ and .pyc files
	@echo    make seed           Seed demo data (tenant, agent, templates)
	@echo.

# ─── FIRST-TIME INIT ─────────────────────────────────────────────

.PHONY: init
init: venv install env docker wait migrate seed ## One-time full setup for new users
	@echo.
	@echo  ═══════════════════════════════════════════════════
	@echo   Setup complete!
	@echo.
	@echo   Run 'make all' to start all services, then open:
	@echo     Frontend : http://localhost:8090
	@echo     Backend  : http://localhost:8000/health
	@echo  ═══════════════════════════════════════════════════

.PHONY: venv
venv: ## Create Python virtual environment + install uv
	@if not exist "$(VENV)\Scripts\activate.bat" ( \
		echo Creating virtual environment... && \
		python -m venv $(VENV) && \
		$(PYTHON) -m pip install --quiet --upgrade pip uv && \
		echo Virtual environment created at $(VENV) \
	) else ( \
		echo Virtual environment already exists at $(VENV) \
	)

.PHONY: env
env: ## Create .env from .env.example if it doesn't exist
	@if not exist ".env" ( \
		if exist ".env.example" ( \
			copy .env.example .env >nul && \
			echo Created .env from .env.example — edit it with your GROQ_API_KEY \
		) else ( \
			echo .env.example not found — skipping. Create .env manually. \
		) \
	) else ( \
		echo .env already exists — skipping. \
	)

# ─── START SERVICES ───────────────────────────────────────────────

.PHONY: all
all: docker wait backend-bg frontend-bg ## Start everything
	@echo.
	@echo  ═══════════════════════════════════════════════════
	@echo   All services started!
	@echo.
	@echo   Frontend : http://localhost:8090
	@echo   Backend  : http://localhost:8000
	@echo   Postgres : localhost:5433
	@echo   MinIO    : localhost:9002
	@echo   ChromaDB : localhost:8002
	@echo   Redis    : localhost:6379
	@echo  ═══════════════════════════════════════════════════

.PHONY: docker
docker: ## Start Docker services (Postgres, MinIO, ChromaDB, Redis)
	docker compose up -d postgres minio chroma redis
	@echo Docker services started.

.PHONY: docker-all
docker-all: ## Start all Docker services including TTS (needs GPU)
	docker compose up -d
	@echo All Docker services started (including TTS).

.PHONY: wait
wait:
	@echo Waiting for services to be ready...
	@timeout /t 10 /nobreak > nul

.PHONY: backend
backend: ## Start FastAPI backend (foreground, port 8000)
	cd backend && $(PYTHON) -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

.PHONY: backend-bg
backend-bg: ## Start FastAPI backend (background window)
	cmd /c start "VoiceFlow Backend" cmd /k "cd /d %CD%\backend && $(PYTHON) -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

.PHONY: frontend
frontend: ## Start Django frontend (foreground, port 8090)
	cd frontend && $(PYTHON) manage.py runserver 8090

.PHONY: frontend-bg
frontend-bg: ## Start Django frontend (background window)
	cmd /c start "VoiceFlow Frontend" cmd /k "cd /d %CD%\frontend && $(PYTHON) manage.py runserver 8090"

# ─── STOP SERVICES ────────────────────────────────────────────────

.PHONY: stop
stop: stop-docker ## Stop all services
	@echo Stopping Python servers...
	-@for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
	-@for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8090 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
	@echo All services stopped.

.PHONY: stop-docker
stop-docker: ## Stop Docker containers
	docker compose down

# ─── SETUP ────────────────────────────────────────────────────────

.PHONY: install
install: ## Install all Python dependencies via uv
	@if exist "$(UV)" ( \
		$(UV) pip install -r requirements.txt \
	) else ( \
		$(PYTHON) -m pip install --upgrade pip uv && \
		$(VENV)\Scripts\uv.exe pip install -r requirements.txt \
	)

.PHONY: migrate
migrate: ## Run Django database migrations
	cd frontend && $(PYTHON) manage.py makemigrations core
	cd frontend && $(PYTHON) manage.py migrate

.PHONY: superuser
superuser: ## Create Django admin superuser
	cd frontend && $(PYTHON) manage.py createsuperuser

.PHONY: seed
seed: ## Seed demo data via backend startup
	@echo Seeding demo data (run backend once to trigger auto-seed)...
	@cd backend && $(PYTHON) -c "from app.database import init_db; import asyncio; asyncio.run(init_db())" 2>nul || echo   Seed will run automatically on first backend start.

.PHONY: setup
setup: install docker wait migrate ## Setup without venv creation
	@echo.
	@echo  Setup complete! Run 'make all' to start.

# ─── DATABASE ─────────────────────────────────────────────────────

.PHONY: db-shell
db-shell: ## Open psql shell
	docker compose exec postgres psql -U vf_admin -d voiceflow_prod

.PHONY: db-tables
db-tables: ## List database tables
	docker compose exec postgres psql -U vf_admin -d voiceflow_prod -c "\dt"

.PHONY: db-agents
db-agents: ## Show agents in database
	docker compose exec postgres psql -U vf_admin -d voiceflow_prod -c "SELECT id, name, status, \"tenantId\" FROM agents ORDER BY \"createdAt\" DESC;"

# ─── TESTING ──────────────────────────────────────────────────────

.PHONY: test
test: ## Quick health check — verify backend + frontend are running
	@$(PYTHON) -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health'); print('Backend  OK:', r.status)"
	@$(PYTHON) -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8090/'); print('Frontend OK:', r.status)"

.PHONY: test-endpoints
test-endpoints: ## Run comprehensive API endpoint validation
	cd .. && $(PYTHON) test_all_endpoints.py

.PHONY: test-rag
test-rag: ## Run document upload + RAG retrieval E2E test
	cd .. && $(PYTHON) test_rag_pipeline.py

# ─── UTILS ────────────────────────────────────────────────────────

.PHONY: status
status: ## Show status of all services
	@echo.
	@echo  Docker containers:
	@docker compose ps 2>nul || echo   (Docker not running)
	@echo.
	@echo  Port 8000 (Backend):
	@netstat -aon | findstr :8000 | findstr LISTENING || echo   Not running
	@echo  Port 8090 (Frontend):
	@netstat -aon | findstr :8090 | findstr LISTENING || echo   Not running
	@echo.

.PHONY: logs
logs: ## Tail Docker logs
	docker compose logs -f

.PHONY: logs-postgres
logs-postgres: ## Tail Postgres logs
	docker compose logs -f postgres

.PHONY: clean
clean: ## Remove __pycache__ and .pyc files
	@for /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
	@del /s /q *.pyc 2>nul
	@echo Cleaned.

.PHONY: reset
reset: stop-docker clean ## Stop everything, remove containers, clean caches
	docker compose down -v
	@echo All services stopped and volumes removed.
