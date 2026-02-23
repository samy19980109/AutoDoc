# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Install backend with dev tools
pip install -e ".[dev]"

# Start infrastructure (PostgreSQL on 5433, Redis on 6379)
docker compose up postgres redis -d

# Apply database migrations
alembic upgrade head

# Run all services via Docker
docker compose up
```

### Running Services Locally

```bash
# API Gateway (port 8000)
uvicorn services.api-gateway.main:app --port 8000 --reload

# GitHub Webhook Handler (port 8001)
uvicorn services.github-webhook.main:app --port 8001 --reload

# Doc Sync Service (port 8002)
uvicorn services.doc-sync.main:app --port 8002 --reload

# Celery Workers
celery -A services.doc_processor.celery_app worker --loglevel=info

# Celery Beat (scheduler)
celery -A services.doc_processor.celery_app beat --loglevel=info

# Dashboard (React frontend, port 3000)
cd dashboard && npm install && npm run dev
```

### Testing & Linting

```bash
pytest                    # full test suite
pytest -k <pattern>       # run specific tests
pytest --cov              # with coverage
ruff check .              # lint
```

## Architecture

This is a **microservices** system that automatically generates and maintains documentation (Confluence/Notion) from GitHub repositories. Services communicate via Redis (Celery task queue) and HTTP.

### Services

| Service | Port | Purpose |
|---------|------|---------|
| **api-gateway** | 8000 | REST API for admin operations, serves React dashboard, JWT auth |
| **github-webhook** | 8001 | Receives GitHub push/PR webhooks, validates HMAC signatures, enqueues Celery jobs |
| **doc-processor** | (worker) | Celery workers: fetches code from GitHub, analyzes with AI, generates docs, calls doc-sync |
| **doc-sync** | 8002 | Destination-agnostic sync to Confluence or Notion, manages page mappings |
| **atlassian-sync** | — | **Deprecated** — replaced by doc-sync |

### Data Flow

```
GitHub Webhook → github-webhook (validate, create Job) → Celery Redis queue
  → doc-processor worker (AI analysis → doc generation → smart merge)
  → HTTP to doc-sync /sync → Confluence or Notion provider → PageMapping stored
```

### Shared Module (`common/`)

- `config/settings.py` — Pydantic Settings with `AUTODOC_` env prefix
- `models/tables.py` — SQLAlchemy ORM: `Repository`, `Job`, `PageMapping`, `ProcessingLog`
- `models/schemas.py` — Pydantic request/response schemas
- `ai/provider.py` — Abstract `AIProvider` with `AnthropicProvider` and `OpenAIProvider` implementations

### Key Patterns

- **Provider abstraction**: Both AI providers and sync destinations use abstract base classes with factory functions (`get_ai_provider()`, `get_sync_provider()`)
- **Smart merge**: HTML comment markers (`<!-- AUTO-DOC:START section="name" -->` ... `<!-- AUTO-DOC:END -->`) delineate AI-generated sections, preserving human-written content during updates
- **Namespace workaround**: Service dirs use dashes (`github-webhook`) but tests import via underscore mapping in `tests/conftest.py` (e.g., `services_github_webhook`)

### Database

PostgreSQL via SQLAlchemy + Alembic migrations in `migrations/versions/`. Tables: `repositories`, `jobs`, `page_mappings`, `processing_logs`.

### Frontend (`dashboard/`)

React 18 + Vite + Tailwind CSS. Pages: Repos, RepoDetail, Jobs, JobDetail, Mappings, Settings. API client in `src/api/client.js`.

## Configuration

All runtime config uses `AUTODOC_` prefixed environment variables (Pydantic Settings). Copy `.env.example` to `.env` for local dev. Key groups: database/Redis URLs, GitHub token/webhook secret, AI provider keys, Confluence/Notion/JIRA credentials, API gateway auth settings.

## Code Style

- Python: snake_case functions/files, PascalCase classes, 100-char line limit
- Lint: `ruff check .` (rules: E, F, I, N, W)
- React: PascalCase component files, camelCase helpers
- Tests: `pytest` + `pytest-asyncio` (asyncio_mode=auto), domain-mirrored folders under `tests/`
- Commits: short imperative subjects, one logical change per commit
