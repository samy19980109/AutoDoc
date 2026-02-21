"""Doc Sync Service -- FastAPI application.

Manages documentation sync to multiple destinations (Confluence, Notion)
and JIRA ticket linking.
"""

import logging
from urllib.parse import urlparse
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from common.config import get_settings
from common.models import (
    DestinationPlatform,
    DocType,
    PageMapping,
    PageMappingResponse,
    Repository,
    SyncRequest,
    SyncResponse,
    get_db,
)

from .jira_client import JiraClient
from .page_mapper import sync_to_destination
from .sync_provider import get_sync_provider

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Doc Sync Service",
    description="Syncs generated documentation to Confluence, Notion, and other destinations.",
    version="0.2.0",
)


# ======================================================================
# Request / response schemas (JIRA-specific, kept local)
# ======================================================================


class JiraLinkRequest(BaseModel):
    ticket_key: str
    page_id: str
    page_title: str
    platform: DestinationPlatform = DestinationPlatform.confluence


class JiraLinkResponse(BaseModel):
    success: bool
    ticket_key: str


def _doc_type_label(doc_type: DocType) -> str:
    labels = {
        DocType.architecture: "Architecture Blueprint",
        DocType.api_reference: "API Reference Guide",
        DocType.walkthrough: "Developer Walkthrough",
    }
    return labels.get(doc_type, doc_type.value.replace("_", " ").title())


def _repo_display_name(repo: Optional[Repository], repo_id: int) -> str:
    if not repo or not repo.github_url:
        return f"Repo {repo_id}"

    parsed = urlparse(repo.github_url)
    if parsed.netloc and parsed.path:
        path = parsed.path.strip("/")
    else:
        path = repo.github_url.replace("https://github.com/", "").strip("/")
    return path.removesuffix(".git") or f"Repo {repo_id}"


def _code_scope_label(code_path: str) -> str:
    if not code_path or code_path == "/":
        return "Repository Overview"
    path = code_path.strip("/")
    return path if path else "Repository Overview"


def _default_doc_title(
    repo: Optional[Repository],
    repo_id: int,
    doc_type: DocType,
    code_path: str,
) -> str:
    return f"{_doc_type_label(doc_type)} | {_repo_display_name(repo, repo_id)} | {_code_scope_label(code_path)}"


# ======================================================================
# Health check
# ======================================================================


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "doc-sync"}


# ======================================================================
# Documentation sync (generic)
# ======================================================================


@app.post("/sync", response_model=SyncResponse)
def sync_doc(
    request: SyncRequest,
    session: Session = Depends(get_db),
):
    """Sync documentation content to the configured destination platform.

    Routes to the correct provider (Confluence, Notion) based on the
    destination_platform field.
    """
    platform = request.destination_platform.value
    config = request.destination_config
    repo = session.query(Repository).filter(Repository.id == request.repo_id).first()

    # If no config provided, try to load from repository
    if not config:
        if repo and repo.destination_config:
            config = repo.destination_config

    if not config:
        raise HTTPException(
            status_code=400,
            detail="No destination config provided and none configured on the repository.",
        )

    title = request.title or _default_doc_title(
        repo=repo,
        repo_id=request.repo_id,
        doc_type=request.doc_type,
        code_path=request.code_path,
    )

    page_id = sync_to_destination(
        session=session,
        repo_id=request.repo_id,
        code_path=request.code_path,
        doc_type=request.doc_type,
        title=title,
        content=request.content,
        platform=platform,
        config=config,
    )

    if not page_id:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to sync page to {platform}. Check service logs for details.",
        )

    session.commit()

    provider = get_sync_provider(platform)
    page_url = provider.get_page_url(page_id)
    return SyncResponse(destination_page_id=page_id, page_url=page_url)


# ======================================================================
# JIRA linking
# ======================================================================


@app.post("/jira/link", response_model=JiraLinkResponse)
def link_jira_ticket(request: JiraLinkRequest):
    """Add a documentation link as a comment on a JIRA ticket."""
    provider = get_sync_provider(request.platform.value)
    page_url = provider.get_page_url(request.page_id)

    comment = (
        f"Documentation has been auto-generated and published:\n\n"
        f"*[{request.page_title}|{page_url}]*"
    )

    jira = JiraClient()
    ok = jira.add_comment(request.ticket_key, comment)

    if not ok:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to add comment to JIRA ticket {request.ticket_key}.",
        )

    return JiraLinkResponse(success=True, ticket_key=request.ticket_key)


# ======================================================================
# Page listings
# ======================================================================


@app.get("/pages/{repo_id}", response_model=list[PageMappingResponse])
def list_pages(repo_id: int, session: Session = Depends(get_db)):
    """List all page mappings for a given repository."""
    repo = session.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    mappings = (
        session.query(PageMapping)
        .filter(PageMapping.repo_id == repo_id)
        .order_by(PageMapping.code_path)
        .all()
    )
    return mappings
