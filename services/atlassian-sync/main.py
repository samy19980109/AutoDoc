"""Atlassian Sync Service -- FastAPI application.

Manages Confluence page creation/updates and JIRA ticket linking for
auto-generated documentation.
"""

import logging
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from common.config import get_settings
from common.models import DocType, PageMapping, Repository, get_db, PageMappingResponse

from .confluence_client import ConfluenceClient
from .jira_client import JiraClient
from .page_mapper import sync_to_confluence

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Atlassian Sync Service",
    description="Syncs generated documentation to Confluence and links JIRA tickets.",
    version="0.1.0",
)


# ======================================================================
# Request / response schemas
# ======================================================================


class SyncRequest(BaseModel):
    """Payload for the POST /sync endpoint."""

    repo_id: int
    code_path: str
    doc_type: DocType
    content: str
    title: Optional[str] = None
    space_key: Optional[str] = None
    parent_page_id: Optional[str] = None


class SyncResponse(BaseModel):
    confluence_page_id: str
    page_url: str


class JiraLinkRequest(BaseModel):
    """Payload for the POST /jira/link endpoint."""

    ticket_key: str
    confluence_page_id: str
    page_title: str


class JiraLinkResponse(BaseModel):
    success: bool
    ticket_key: str


# ======================================================================
# Health check
# ======================================================================


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "atlassian-sync"}


# ======================================================================
# Confluence sync
# ======================================================================


@app.post("/sync", response_model=SyncResponse)
def sync_doc_to_confluence(
    request: SyncRequest,
    session: Session = Depends(get_db),
):
    """Sync documentation content to a Confluence page.

    If a PageMapping already exists for this (repo_id, code_path, doc_type)
    combination the existing page is updated; otherwise a new page is created.
    """
    settings = get_settings()

    # Resolve the Confluence space key.
    space_key = request.space_key
    if not space_key:
        repo = session.query(Repository).filter(Repository.id == request.repo_id).first()
        if repo and repo.confluence_space_key:
            space_key = repo.confluence_space_key
    if not space_key:
        raise HTTPException(
            status_code=400,
            detail="No Confluence space key provided and none configured on the repository.",
        )

    # Build a page title if not supplied.
    title = request.title or f"{request.doc_type.value}: {request.code_path}"

    page_id = sync_to_confluence(
        session=session,
        repo_id=request.repo_id,
        code_path=request.code_path,
        doc_type=request.doc_type,
        title=title,
        content=request.content,
        space_key=space_key,
        parent_page_id=request.parent_page_id,
    )

    if not page_id:
        raise HTTPException(
            status_code=502,
            detail="Failed to sync page to Confluence. Check service logs for details.",
        )

    session.commit()

    page_url = f"{settings.confluence_url.rstrip('/')}/pages/{page_id}"
    return SyncResponse(confluence_page_id=page_id, page_url=page_url)


# ======================================================================
# JIRA linking
# ======================================================================


@app.post("/jira/link", response_model=JiraLinkResponse)
def link_jira_ticket(request: JiraLinkRequest):
    """Add a documentation link as a comment on a JIRA ticket."""
    settings = get_settings()
    page_url = f"{settings.confluence_url.rstrip('/')}/pages/{request.confluence_page_id}"

    comment = (
        f"Documentation has been auto-generated and published to Confluence:\n\n"
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
    """List all Confluence page mappings for a given repository."""
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
