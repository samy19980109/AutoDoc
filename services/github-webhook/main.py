"""GitHub Webhook Service -- FastAPI application."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from common.config import get_settings
from common.models import Job, JobResponse, Repository, TriggerType, get_db

from .webhook_handler import (
    create_and_enqueue_job,
    parse_pull_request_event,
    parse_push_event,
    validate_signature,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="GitHub Webhook Service",
    description="Receives GitHub webhooks and enqueues documentation processing jobs.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "github-webhook"}


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------


@app.post("/webhook", tags=["webhook"])
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
    x_github_event: str = Header(default="", alias="X-GitHub-Event"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Receive and process a GitHub webhook delivery."""

    body = await request.body()

    # -- Signature validation --------------------------------------------------
    if not validate_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload: dict[str, Any] = await request.json()

    # -- Ping event (webhook registration handshake) ---------------------------
    if x_github_event == "ping":
        return {"message": "pong", "zen": payload.get("zen", "")}

    # -- Push event ------------------------------------------------------------
    if x_github_event == "push":
        parsed = parse_push_event(payload)
        if parsed is None:
            return {"message": "Push event ignored (tag, deletion, or non-branch ref)"}

        job = create_and_enqueue_job(
            db=db,
            repo_url=parsed["repo_url"],
            branch=parsed["branch"],
            changed_files=parsed["changed_files"],
            trigger_type=TriggerType.webhook,
        )
        return {"message": "Job created", "job_id": job.id}

    # -- Pull request event ----------------------------------------------------
    if x_github_event == "pull_request":
        parsed = parse_pull_request_event(payload)
        if parsed is None:
            return {"message": "Pull request event ignored (not a merge)"}

        job = create_and_enqueue_job(
            db=db,
            repo_url=parsed["repo_url"],
            branch=parsed["branch"],
            changed_files=parsed["changed_files"],
            trigger_type=TriggerType.webhook,
        )
        return {
            "message": "Job created from merged PR",
            "job_id": job.id,
            "pr_number": parsed.get("pr_number"),
        }

    # -- Unsupported event -----------------------------------------------------
    return {"message": f"Event '{x_github_event}' is not handled"}


# ---------------------------------------------------------------------------
# On-demand trigger endpoint
# ---------------------------------------------------------------------------


class TriggerRequest(BaseModel):
    repo_id: int


@app.post("/trigger", response_model=JobResponse, tags=["trigger"])
def trigger_job(
    body: TriggerRequest,
    db: Session = Depends(get_db),
) -> Job:
    """Manually trigger a documentation processing job for a registered repository."""

    repository = db.query(Repository).filter(Repository.id == body.repo_id).first()
    if repository is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    job = create_and_enqueue_job(
        db=db,
        repo_url=repository.github_url,
        branch=repository.default_branch,
        changed_files=[],  # full scan -- no specific changed files
        trigger_type=TriggerType.manual,
    )
    return job
