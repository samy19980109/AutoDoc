"""API Gateway -- main FastAPI application for the Enterprise Auto-Documentation system."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from common.config import get_settings
from common.models import Base, get_engine
from .auth.dependencies import create_access_token, verify_token
from .routes.repositories import router as repositories_router
from .routes.jobs import router as jobs_router
from .routes.mappings import router as mappings_router

logger = logging.getLogger("api_gateway")
settings = get_settings()

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    logger.info("API Gateway starting up")
    # Ensure tables exist (in dev; production should use Alembic migrations)
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified")
    yield
    logger.info("API Gateway shutting down")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AutoDoc API Gateway",
    description="REST API for the Enterprise Auto-Documentation system",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth route (lightweight, lives in main to avoid circular imports)
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/api/auth/login", response_model=TokenResponse, tags=["auth"])
def login(body: LoginRequest):
    """Simple username/password login that returns a JWT.

    Credentials are checked against AUTODOC_DASHBOARD_USER and
    AUTODOC_DASHBOARD_PASSWORD environment variables (defaults: admin/admin).
    """
    import os

    expected_user = os.getenv("AUTODOC_DASHBOARD_USER", "admin")
    expected_pass = os.getenv("AUTODOC_DASHBOARD_PASSWORD", "admin")

    if body.username != expected_user or body.password != expected_pass:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid credentials"},
        )

    token = create_access_token(subject=body.username)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(repositories_router)
app.include_router(jobs_router)
app.include_router(mappings_router)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
def health_check():
    """Lightweight health check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Static files -- serve React dashboard build if available
# ---------------------------------------------------------------------------

_dashboard_dist = Path(__file__).resolve().parent.parent.parent / "dashboard" / "dist"
if _dashboard_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_dashboard_dist), html=True), name="dashboard")
