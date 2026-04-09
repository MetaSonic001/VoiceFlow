# ═══════════════════════════════════════════════════════════════════
# VoiceFlow — Makefile
# Run from: python/ directory
# ═══════════════════════════════════════════════════════════════════

SHELL := cmd.exe
VENV := ..\.venv
PYTHON := $(VENV)\Scripts\python.exe
PIP := $(PYTHON) -m pip

# ─── Convenience ──────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@echo.
	@echo  VoiceFlow Commands
	@echo  ══════════════════════════════════════════════════
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
	@echo    make install        Install all Python dependencies
	@echo    make migrate        Run Django migrations
	@echo    make superuser      Create Django admin superuser
	@echo    make setup          Full first-time setup (install + migrate)
	@echo.
	@echo  DATABASE
	@echo    make db-shell       Open psql shell
	@echo    make db-tables      List all database tables
	@echo    make db-agents      List agents in database
	@echo.
	@echo  UTILS
	@echo    make status         Show status of all services
	@echo    make logs           Tail Docker logs
	@echo    make clean          Remove __pycache__ and .pyc files
	@echo.

# ─── START SERVICES ───────────────────────────────────────────────

.PHONY: all
all: docker wait backend-bg frontend-bg ## Start everything
	@echo.
	@echo  ═══════════════════════════════════════════
	@echo   All services started!
	@echo   Frontend : http://localhost:8090
	@echo   Backend  : http://localhost:8000
	@echo   Postgres : localhost:5433
	@echo   MinIO    : localhost:9001
	@echo   ChromaDB : localhost:8002
	@echo   Redis    : localhost:6379
	@echo  ═══════════════════════════════════════════

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
	@echo Waiting for Postgres to be ready...
	@timeout /t 8 /nobreak > nul

.PHONY: backend
backend: ## Start FastAPI backend (foreground, port 8000)
	cd backend && $(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: backend-bg
backend-bg: ## Start FastAPI backend (background window)
	start "VoiceFlow Backend" cmd /k "cd /d %CD%\backend && $(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

.PHONY: frontend
frontend: ## Start Django frontend (foreground, port 8090)
	cd frontend && $(PYTHON) manage.py runserver 8090

.PHONY: frontend-bg
frontend-bg: ## Start Django frontend (background window)
	start "VoiceFlow Frontend" cmd /k "cd /d %CD%\frontend && $(PYTHON) manage.py runserver 8090"

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
install: ## Install all Python dependencies
	$(PIP) install -r requirements.txt

.PHONY: migrate
migrate: ## Run Django database migrations
	cd frontend && $(PYTHON) manage.py makemigrations core
	cd frontend && $(PYTHON) manage.py migrate

.PHONY: superuser
superuser: ## Create Django admin superuser
	cd frontend && $(PYTHON) manage.py createsuperuser

.PHONY: setup
setup: install migrate ## Full first-time setup
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
	docker compose exec postgres psql -U vf_admin -d voiceflow_prod -c "SELECT id, name, status, tenant_id FROM agents ORDER BY created_at DESC;"

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

.PHONY: test
test: ## Run E2E test against running services
	cd frontend && $(PYTHON) -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8090/'); print('Frontend OK:', r.status)"
	cd frontend && $(PYTHON) -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health'); print('Backend OK:', r.status)"
