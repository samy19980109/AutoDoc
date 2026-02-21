"""Core webhook processing logic: signature validation, event parsing, job creation."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Optional

from celery import Celery
from sqlalchemy.orm import Session

from common.config import get_settings
from common.models import (
    Job,
    JobPayload,
    JobStatus,
    Repository,
    TriggerType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery application (used only for .send_task -- workers run separately)
# ---------------------------------------------------------------------------

_celery_app: Optional[Celery] = None


def _get_celery_app() -> Celery:
    global _celery_app
    if _celery_app is None:
        settings = get_settings()
        _celery_app = Celery(broker=settings.celery_broker_url)
    return _celery_app


# ---------------------------------------------------------------------------
# Signature validation
# ---------------------------------------------------------------------------


def validate_signature(payload_body: bytes, signature_header: str) -> bool:
    """Validate the ``X-Hub-Signature-256`` header against the shared secret.

    Args:
        payload_body: Raw request body bytes.
        signature_header: Value of the ``X-Hub-Signature-256`` header
            (e.g. ``sha256=abcdef…``).

    Returns:
        ``True`` when the signature is valid.
    """
    settings = get_settings()
    if not settings.github_webhook_secret:
        logger.warning("Webhook secret is not configured -- skipping validation")
        return True

    if not signature_header:
        return False

    hash_algorithm, _, remote_signature = signature_header.partition("=")
    if hash_algorithm != "sha256":
        return False

    local_signature = hmac.new(
        settings.github_webhook_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(local_signature, remote_signature)


# ---------------------------------------------------------------------------
# Event parsing helpers
# ---------------------------------------------------------------------------


def parse_push_event(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Extract relevant fields from a GitHub ``push`` event payload.

    Returns ``None`` when the push should be ignored (e.g. tag pushes,
    branch deletions).
    """
    ref: str = payload.get("ref", "")
    if not ref.startswith("refs/heads/"):
        return None

    # Ignore branch deletions (after SHA is all zeroes).
    if payload.get("deleted", False):
        return None

    branch = ref.removeprefix("refs/heads/")
    repo_data = payload.get("repository", {})
    repo_full_name = repo_data.get("full_name", "")
    repo_url = repo_data.get("html_url", "")

    # Collect changed file paths across all commits in the push.
    changed_files: set[str] = set()
    for commit in payload.get("commits", []):
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))
        changed_files.update(commit.get("removed", []))

    before_sha = payload.get("before", "")
    after_sha = payload.get("after", "")

    return {
        "repo_full_name": repo_full_name,
        "repo_url": repo_url,
        "branch": branch,
        "changed_files": sorted(changed_files),
        "before_sha": before_sha,
        "after_sha": after_sha,
    }


def parse_pull_request_event(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Extract relevant fields from a GitHub ``pull_request`` event payload.

    Only merged pull requests are processed; all other actions are ignored.
    """
    action = payload.get("action", "")
    pr = payload.get("pull_request", {})
    merged = pr.get("merged", False)

    if action != "closed" or not merged:
        return None

    repo_data = payload.get("repository", {})
    base_branch = pr.get("base", {}).get("ref", "main")

    changed_files: list[str] = []
    # The PR payload does not include the file list directly; downstream
    # consumers can fetch it via the GitHub API if needed.  We store an empty
    # list here and let the processing pipeline resolve it.

    return {
        "repo_full_name": repo_data.get("full_name", ""),
        "repo_url": repo_data.get("html_url", ""),
        "branch": base_branch,
        "changed_files": changed_files,
        "pr_number": pr.get("number"),
        "pr_title": pr.get("title", ""),
        "merge_commit_sha": pr.get("merge_commit_sha", ""),
    }


# ---------------------------------------------------------------------------
# Job creation & enqueuing
# ---------------------------------------------------------------------------


def create_and_enqueue_job(
    db: Session,
    repo_url: str,
    branch: str,
    changed_files: list[str],
    trigger_type: TriggerType,
) -> Job:
    """Persist a new :class:`Job` and dispatch it to the Celery task queue.

    If the repository is not yet registered in the database it will be created
    automatically with sensible defaults.

    Returns:
        The newly created :class:`Job` instance (already committed).
    """
    # Upsert repository -------------------------------------------------------
    repository = db.query(Repository).filter(Repository.github_url == repo_url).first()
    if repository is None:
        repository = Repository(
            github_url=repo_url,
            default_branch=branch,
        )
        db.add(repository)
        db.flush()  # ensure we get an id
        logger.info("Auto-registered repository %s (id=%s)", repo_url, repository.id)

    # Create job ---------------------------------------------------------------
    job = Job(
        repo_id=repository.id,
        trigger_type=trigger_type,
        status=JobStatus.pending,
    )
    db.add(job)
    db.flush()

    # Build Celery payload -----------------------------------------------------
    payload = JobPayload(
        job_id=job.id,
        repo_id=repository.id,
        github_url=repo_url,
        branch=branch,
        changed_files=changed_files,
        trigger_type=trigger_type,
        destination_platform=repository.destination_platform or "confluence",
        destination_config=repository.destination_config or {},
    )

    db.commit()

    # Dispatch -----------------------------------------------------------------
    celery_app = _get_celery_app()
    celery_app.send_task("process_documentation", args=[payload.model_dump_json()])
    logger.info(
        "Enqueued job %s for repo %s (trigger=%s, files=%d)",
        job.id,
        repo_url,
        trigger_type.value,
        len(changed_files),
    )

    return job
