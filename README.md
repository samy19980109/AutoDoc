# Enterprise Auto-Documentation from Code

AI-powered system that automatically generates, updates, and maintains Confluence documentation from GitHub repositories, and links relevant docs back to JIRA tickets.

## Architecture

```
services/
├── api-gateway/          # FastAPI REST API + serves dashboard
├── github-webhook/       # Receives GitHub webhooks, fetches code
├── doc-processor/        # Celery workers: AI analysis + doc generation
└── atlassian-sync/       # Confluence CRUD + JIRA ticket updates
common/                   # Shared models, utils, AI provider abstraction
dashboard/                # React + Vite + Tailwind admin UI
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for dashboard development)

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

### 2. Start Infrastructure

```bash
docker compose up postgres redis -d
```

### 3. Run Migrations

```bash
pip install -e .
alembic upgrade head
```

### 4. Start Services

**Option A: Docker Compose (all services)**
```bash
docker compose up
```

**Option B: Local development (individual services)**
```bash
# Terminal 1: API Gateway
uvicorn services.api-gateway.main:app --port 8000 --reload

# Terminal 2: GitHub Webhook Handler
uvicorn services.github-webhook.main:app --port 8001 --reload

# Terminal 3: Atlassian Sync
uvicorn services.atlassian-sync.main:app --port 8002 --reload

# Terminal 4: Celery Worker
celery -A services.doc_processor.celery_app worker --loglevel=info

# Terminal 5: Celery Beat (scheduler)
celery -A services.doc_processor.celery_app beat --loglevel=info
```

### 5. Dashboard Development

```bash
cd dashboard
npm install
npm run dev
```

Dashboard runs at http://localhost:3000 and proxies API calls to the gateway.

## Configuration

All configuration is via environment variables prefixed with `AUTODOC_`. See `.env.example` for the full list.

| Variable | Description |
|----------|-------------|
| `AUTODOC_DATABASE_URL` | PostgreSQL connection string |
| `AUTODOC_REDIS_URL` | Redis connection string |
| `AUTODOC_GITHUB_TOKEN` | GitHub personal access token |
| `AUTODOC_GITHUB_WEBHOOK_SECRET` | Secret for webhook HMAC validation |
| `AUTODOC_AI_PROVIDER` | `anthropic` or `openai` |
| `AUTODOC_ANTHROPIC_API_KEY` | Anthropic API key |
| `AUTODOC_OPENAI_API_KEY` | OpenAI API key |
| `AUTODOC_CONFLUENCE_URL` | Confluence base URL |
| `AUTODOC_CONFLUENCE_USERNAME` | Confluence username/email |
| `AUTODOC_CONFLUENCE_API_TOKEN` | Confluence API token |
| `AUTODOC_JIRA_URL` | JIRA base URL |
| `AUTODOC_JIRA_USERNAME` | JIRA username/email |
| `AUTODOC_JIRA_API_TOKEN` | JIRA API token |

## How It Works

1. **Trigger**: A GitHub webhook fires on push/merge, or docs are triggered manually via the dashboard
2. **Fetch**: The webhook service clones/fetches the repo and identifies changed files
3. **Analyze**: Celery workers send code to AI (Claude or GPT-4) for structured analysis
4. **Generate**: AI generates documentation (API reference, architecture docs, walkthroughs)
5. **Smart Merge**: AI-generated sections are wrapped in `<!-- AUTO-DOC -->` markers; human-written content is preserved
6. **Sync**: Documentation is pushed to Confluence; related JIRA tickets get doc links

## Smart Merge

AI-generated content is wrapped in HTML comment markers:

```html
<!-- AUTO-DOC:START section="api-reference" -->
<h2>API Reference</h2>
...
<!-- AUTO-DOC:END -->
```

Human-written content outside these markers is preserved during updates.

## API Endpoints

### API Gateway (port 8000)
- `GET /api/repos` - List repositories
- `POST /api/repos` - Add repository
- `POST /api/repos/{id}/trigger` - Trigger doc generation
- `GET /api/jobs` - List jobs
- `GET /api/jobs/{id}/logs` - Get job logs

### GitHub Webhook (port 8001)
- `POST /webhook` - GitHub webhook endpoint
- `POST /trigger` - Manual trigger

### Atlassian Sync (port 8002)
- `POST /sync` - Sync doc to Confluence
- `POST /jira/link` - Add doc link to JIRA ticket

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## Tech Stack

- **Backend**: FastAPI, Celery, SQLAlchemy, Alembic
- **AI**: Anthropic Claude, OpenAI GPT-4 (abstracted)
- **Integrations**: PyGithub, atlassian-python-api
- **Frontend**: React 18, Vite, Tailwind CSS
- **Infrastructure**: PostgreSQL, Redis, Docker
