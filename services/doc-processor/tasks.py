"""Celery tasks for the doc-processor service."""

from __future__ import annotations

import json
import traceback
from datetime import datetime

import httpx

try:
    from celery_app import app
except ImportError:
    from services.doc_processor.celery_app import app
from common.ai import get_ai_provider
from common.config import get_settings
from common.models import (
    DestinationPlatform,
    DocType,
    Job,
    JobPayload,
    JobStatus,
    ProcessingLog,
    Repository,
    TriggerType,
)
from common.models.base import get_session_factory
from common.utils.logging import setup_logging
from github import Github, GithubException
from analyzer import analyze_code
from generator import generate_docs
from merger import merge_content

logger = setup_logging("doc-processor.tasks")

# File extensions worth analyzing
_ANALYZABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb",
}

# Paths to skip
_IGNORE_PREFIXES = (
    "node_modules/", "__pycache__/", ".git/", "dist/", "build/",
    "venv/", ".venv/", ".env", "vendor/",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_log(session, job_id: int, step: str, message: str) -> None:
    """Insert a processing log entry."""
    entry = ProcessingLog(
        job_id=job_id,
        step=step,
        message=message,
        created_at=datetime.utcnow(),
    )
    session.add(entry)
    session.commit()


def _get_ai():
    """Build an AIProvider from current settings."""
    settings = get_settings()
    api_key = (
        settings.anthropic_api_key
        if settings.ai_provider == "anthropic"
        else settings.openai_api_key
    )
    return get_ai_provider(
        provider=settings.ai_provider,
        api_key=api_key,
        model=settings.ai_model,
    )


def _sync_to_destination(
    repo_id: int,
    code_path: str,
    doc_type: str,
    content: str,
    destination_platform: str,
    destination_config: dict,
) -> tuple[bool, str]:
    """Call the doc-sync service via HTTP to publish documentation."""
    settings = get_settings()
    sync_url = settings.doc_sync_url.rstrip("/")

    try:
        resp = httpx.post(
            f"{sync_url}/sync",
            json={
                "repo_id": repo_id,
                "code_path": code_path,
                "doc_type": doc_type,
                "content": content,
                "destination_platform": destination_platform,
                "destination_config": destination_config,
            },
            timeout=120.0,
        )
        if resp.status_code < 300:
            body = resp.json()
            logger.info(
                "Synced %s for repo %d to %s (page_id=%s, page_url=%s)",
                doc_type,
                repo_id,
                destination_platform,
                body.get("destination_page_id", "?"),
                body.get("page_url", "?"),
            )
            return True, ""
        else:
            detail = resp.text
            try:
                parsed = resp.json()
                detail = parsed.get("detail", detail)
            except Exception:
                pass
            logger.error(
                "Doc-sync returned %d for %s repo %d: %s",
                resp.status_code,
                doc_type,
                repo_id,
                detail,
            )
            return False, f"HTTP {resp.status_code}: {detail}"
    except Exception as exc:
        logger.error("Failed to call doc-sync for %s repo %d: %s", doc_type, repo_id, exc)
        return False, str(exc)


# ---------------------------------------------------------------------------
# Main task
# ---------------------------------------------------------------------------

@app.task(
    name="process_documentation",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def process_documentation(self, payload_json: str) -> dict:
    """Orchestrate the full documentation pipeline for a single job.

    Parameters
    ----------
    payload_json:
        JSON-serialised :class:`JobPayload`.

    Returns
    -------
    dict
        Result summary with generated doc types and section counts.
    """
    payload = JobPayload.model_validate_json(payload_json)
    session_factory = get_session_factory()
    session = session_factory()

    try:
        # --- Mark job as processing -----------------------------------
        job: Job | None = session.get(Job, payload.job_id)
        if job is None:
            raise ValueError(f"Job {payload.job_id} not found in database")

        job.status = JobStatus.processing
        job.started_at = datetime.utcnow()
        session.commit()
        _add_log(session, job.id, "start", f"Processing started for {payload.github_url}")

        # --- 1. Gather file contents from GitHub ----------------------
        file_contents: dict[str, str] = {}
        settings = get_settings()
        repo_full_name = payload.github_url.replace("https://github.com/", "")

        try:
            gh = Github(settings.github_token)
            gh_repo = gh.get_repo(repo_full_name)
        except Exception as exc:
            raise RuntimeError(f"Cannot access GitHub repo {repo_full_name}: {exc}")

        if payload.changed_files:
            # Fetch only the changed files
            _add_log(
                session,
                job.id,
                "gather",
                f"Fetching {len(payload.changed_files)} changed files from GitHub",
            )
            for path in payload.changed_files:
                try:
                    ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
                    if ext not in _ANALYZABLE_EXTENSIONS:
                        continue
                    content_file = gh_repo.get_contents(path, ref=payload.branch)
                    if isinstance(content_file, list):
                        continue
                    decoded = content_file.decoded_content.decode("utf-8", errors="replace")
                    file_contents[path] = decoded
                except Exception as exc:
                    logger.warning("Could not fetch %s: %s", path, exc)
        else:
            # Full repo scan — walk the tree
            _add_log(session, job.id, "gather", "Full repo scan: fetching file tree from GitHub")
            try:
                tree = gh_repo.get_git_tree(sha=payload.branch, recursive=True)
                paths_to_fetch = []
                for item in tree.tree:
                    if item.type != "blob":
                        continue
                    if any(item.path.startswith(p) for p in _IGNORE_PREFIXES):
                        continue
                    ext = "." + item.path.rsplit(".", 1)[-1] if "." in item.path else ""
                    if ext not in _ANALYZABLE_EXTENSIONS:
                        continue
                    if item.size and item.size > 100_000:
                        continue
                    paths_to_fetch.append(item.path)

                # Cap at 100 files to avoid very large repos
                paths_to_fetch = paths_to_fetch[:100]
                _add_log(
                    session, job.id, "gather",
                    f"Found {len(paths_to_fetch)} analyzable files",
                )

                for path in paths_to_fetch:
                    try:
                        content_file = gh_repo.get_contents(path, ref=payload.branch)
                        if isinstance(content_file, list):
                            continue
                        decoded = content_file.decoded_content.decode("utf-8", errors="replace")
                        file_contents[path] = decoded
                    except Exception as exc:
                        logger.warning("Could not fetch %s: %s", path, exc)

            except Exception as exc:
                raise RuntimeError(f"Failed to fetch repo tree: {exc}")

        _add_log(
            session, job.id, "gather",
            f"Fetched {len(file_contents)} files ({sum(len(v) for v in file_contents.values())} chars total)",
        )

        # --- 2. Analyze code ------------------------------------------
        _add_log(session, job.id, "analyze", "Starting AI code analysis")
        ai_provider = _get_ai()
        analysis = analyze_code(file_contents, ai_provider)
        _add_log(
            session,
            job.id,
            "analyze",
            f"Analysis complete: {len(analysis.get('functions', []))} functions, "
            f"{len(analysis.get('classes', []))} classes",
        )

        # --- 3. Generate docs for each doc type -----------------------
        generated: dict[str, str] = {}
        for doc_type in DocType:
            _add_log(session, job.id, "generate", f"Generating {doc_type.value} documentation")
            # TODO: fetch existing page content for smart merge
            existing_content = ""
            html = generate_docs(analysis, doc_type, existing_content, ai_provider)
            generated[doc_type.value] = html
            _add_log(
                session,
                job.id,
                "generate",
                f"{doc_type.value} generated ({len(html)} chars)",
            )

        # --- 4. Merge with existing content ---------------------------
        _add_log(session, job.id, "merge", "Merging generated content with existing pages")
        # TODO: fetch existing page bodies from destination
        existing_page_html = ""
        merged = merge_content(existing_page_html, generated)
        _add_log(
            session,
            job.id,
            "merge",
            f"Merge complete ({len(merged)} chars, {len(generated)} sections)",
        )

        # --- 5. Sync to destination -----------------------------------
        _add_log(session, job.id, "sync", "Syncing documentation to destination")
        destination_platform = payload.destination_platform.value
        destination_config = payload.destination_config

        sync_failures: list[str] = []
        for doc_type_key, content in generated.items():
            ok, error_detail = _sync_to_destination(
                repo_id=payload.repo_id,
                code_path="/",
                doc_type=doc_type_key,
                content=content,
                destination_platform=destination_platform,
                destination_config=destination_config,
            )
            if not ok:
                message = f"{doc_type_key}: {error_detail}"
                sync_failures.append(message)
                _add_log(session, job.id, "sync_error", message)

        if sync_failures:
            failed = " | ".join(sync_failures)
            raise RuntimeError(f"Destination sync failed for doc types: {failed}")

        _add_log(
            session,
            job.id,
            "sync",
            f"Sync complete for {len(generated)} doc types to {destination_platform}",
        )

        # --- 6. Mark job complete -------------------------------------
        job.status = JobStatus.completed
        job.completed_at = datetime.utcnow()
        session.commit()
        _add_log(session, job.id, "complete", "Documentation pipeline finished successfully")

        logger.info("Job %d completed successfully", job.id)
        return {
            "job_id": job.id,
            "status": "completed",
            "doc_types": list(generated.keys()),
            "total_chars": sum(len(v) for v in generated.values()),
        }

    except Exception as exc:
        logger.exception("Job %d failed: %s", payload.job_id, exc)
        try:
            job = session.get(Job, payload.job_id)
            if job is not None:
                job.status = JobStatus.failed
                job.completed_at = datetime.utcnow()
                job.error = f"{exc.__class__.__name__}: {exc}"
                session.commit()
            _add_log(
                session,
                payload.job_id,
                "error",
                traceback.format_exc()[-2000:],
            )
        except Exception:
            logger.exception("Failed to persist error state for job %d", payload.job_id)
        finally:
            session.close()

        raise self.retry(exc=exc)

    finally:
        session.close()


# ---------------------------------------------------------------------------
# Scheduled task
# ---------------------------------------------------------------------------

@app.task(name="scheduled_sync")
def scheduled_sync() -> dict:
    """Periodic task that discovers all repositories and enqueues doc-generation jobs."""
    logger.info("Scheduled sync started")
    session_factory = get_session_factory()
    session = session_factory()

    enqueued: list[int] = []
    try:
        repos = session.query(Repository).all()
        if not repos:
            logger.info("No repositories registered; nothing to sync")
            return {"enqueued": 0}

        for repo in repos:
            job = Job(
                repo_id=repo.id,
                trigger_type=TriggerType.scheduled,
                status=JobStatus.pending,
            )
            session.add(job)
            session.commit()

            payload = JobPayload(
                job_id=job.id,
                repo_id=repo.id,
                github_url=repo.github_url,
                branch=repo.default_branch,
                changed_files=[],
                trigger_type=TriggerType.scheduled,
                destination_platform=repo.destination_platform,
                destination_config=repo.destination_config or {},
            )

            process_documentation.apply_async(
                args=[payload.model_dump_json()],
                queue="doc-processing",
            )
            enqueued.append(job.id)
            logger.info("Enqueued job %d for repo %s", job.id, repo.github_url)

        logger.info("Scheduled sync complete: enqueued %d jobs", len(enqueued))
        return {"enqueued": len(enqueued), "job_ids": enqueued}

    except Exception:
        logger.exception("Scheduled sync failed")
        raise

    finally:
        session.close()
