# Repository Guidelines

## Project Structure & Module Organization
- `services/` contains backend microservices: `api-gateway`, `github-webhook`, `doc-processor`, `atlassian-sync`, and `doc-sync`.
- `common/` holds shared config, SQLAlchemy models, AI provider abstractions, and utility code used across services.
- `dashboard/` is the React + Vite admin UI (`src/pages`, `src/api`, `src/App.jsx`).
- `tests/` mirrors service domains (`test_api_gateway`, `test_doc_processor`, etc.) with shared fixtures in `tests/conftest.py`.
- `migrations/` and `alembic.ini` manage database schema changes.

## Build, Test, and Development Commands
- `pip install -e ".[dev]"` installs backend and dev tooling.
- `pytest` runs all backend tests under `tests/`.
- `docker compose up postgres redis -d` starts local infra dependencies.
- `alembic upgrade head` applies DB migrations.
- `docker compose up` starts all services together.
- `uvicorn services.api-gateway.main:app --port 8000 --reload` runs API gateway locally (repeat for other services as needed).
- `celery -A services.doc_processor.celery_app worker --loglevel=info` starts background workers.
- `cd dashboard && npm install && npm run dev` runs frontend on Vite dev server.

## Coding Style & Naming Conventions
- Python: 4-space indentation, max line length 100, type-aware FastAPI/Pydantic patterns.
- Lint with `ruff` (rules: `E,F,I,N,W`); run `ruff check .` before opening a PR.
- Use snake_case for Python files/functions, PascalCase for Pydantic/SQLAlchemy classes.
- React: component files use PascalCase (for example `RepoDetailPage.jsx`); helper modules use lower camel or concise nouns.

## Testing Guidelines
- Framework: `pytest` with `pytest-asyncio` (`asyncio_mode = auto`).
- Place tests in matching domain folders and name files `test_<unit>.py`.
- Prefer focused unit tests for mappers/clients plus API route tests for FastAPI endpoints.
- Use `pytest -k <pattern>` for targeted runs during development.

## Commit & Pull Request Guidelines
- Follow the existing history style: short, imperative commit subjects (for example `Add doc-sync service and Notion support`).
- Keep commits scoped to one logical change; include migration/config updates in the same commit when required.
- PRs should include: purpose, impacted services/modules, test evidence (`pytest` output), and screenshots for dashboard UI changes.
- Link relevant issue/ticket IDs and note any new environment variables (`AUTODOC_*`) or operational steps.

## Security & Configuration Tips
- Do not commit secrets; copy `.env.example` to `.env` locally.
- Keep all runtime config under `AUTODOC_` environment variables for consistency across services.
