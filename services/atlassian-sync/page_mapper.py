"""Page mapping logic between code paths and Confluence pages."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from common.models import DocType, PageMapping, Repository

from .confluence_client import ConfluenceClient

logger = logging.getLogger(__name__)


def get_or_create_mapping(
    session: Session,
    repo_id: int,
    code_path: str,
    doc_type: DocType,
) -> PageMapping:
    """Return an existing PageMapping or create a new one.

    The uniqueness key is (repo_id, code_path, doc_type).
    """
    mapping = (
        session.query(PageMapping)
        .filter(
            PageMapping.repo_id == repo_id,
            PageMapping.code_path == code_path,
            PageMapping.doc_type == doc_type,
        )
        .first()
    )
    if mapping is not None:
        return mapping

    mapping = PageMapping(
        repo_id=repo_id,
        code_path=code_path,
        doc_type=doc_type,
    )
    session.add(mapping)
    session.flush()  # populate mapping.id without committing
    logger.info(
        "Created new PageMapping id=%s for repo=%s path='%s' type=%s",
        mapping.id,
        repo_id,
        code_path,
        doc_type.value,
    )
    return mapping


def update_mapping(
    session: Session,
    mapping_id: int,
    confluence_page_id: str,
) -> Optional[PageMapping]:
    """Set the Confluence page ID and last-synced timestamp on an existing mapping.

    Returns the updated mapping, or ``None`` if the mapping was not found.
    """
    mapping = session.query(PageMapping).filter(PageMapping.id == mapping_id).first()
    if mapping is None:
        logger.warning("PageMapping id=%s not found", mapping_id)
        return None

    mapping.confluence_page_id = confluence_page_id
    mapping.last_synced_at = datetime.utcnow()
    session.flush()
    logger.info(
        "Updated PageMapping id=%s -> confluence_page_id=%s",
        mapping_id,
        confluence_page_id,
    )
    return mapping


def sync_to_confluence(
    session: Session,
    repo_id: int,
    code_path: str,
    doc_type: DocType,
    title: str,
    content: str,
    space_key: str,
    parent_page_id: Optional[str] = None,
) -> str:
    """Full sync flow: mapping lookup -> Confluence create/update -> mapping update.

    Parameters
    ----------
    session:
        Active SQLAlchemy session (caller is responsible for commit/rollback).
    repo_id:
        Repository primary key.
    code_path:
        Relative path inside the repository that this doc covers.
    doc_type:
        Type of documentation being synced.
    title:
        Title for the Confluence page.
    content:
        Page body in Confluence storage format (XHTML).
    space_key:
        Confluence space key.
    parent_page_id:
        Optional parent page ID for hierarchy nesting.

    Returns
    -------
    str
        The Confluence page ID (new or existing), or an empty string on
        failure.
    """
    mapping = get_or_create_mapping(session, repo_id, code_path, doc_type)

    confluence = ConfluenceClient()

    # If a Confluence page already exists, update it.
    if mapping.confluence_page_id:
        existing = confluence.get_page(mapping.confluence_page_id)
        if existing:
            ok = confluence.update_page(mapping.confluence_page_id, title, content)
            if ok:
                update_mapping(session, mapping.id, mapping.confluence_page_id)
                return mapping.confluence_page_id
            logger.error(
                "Failed to update existing page %s; will attempt to create new page",
                mapping.confluence_page_id,
            )
        else:
            logger.warning(
                "Mapped page %s no longer exists; creating a new page",
                mapping.confluence_page_id,
            )

    # Create a new page.
    page_id = confluence.create_page(
        space_key=space_key,
        title=title,
        body=content,
        parent_id=parent_page_id,
    )
    if not page_id:
        logger.error(
            "Failed to create Confluence page for repo=%s path='%s'",
            repo_id,
            code_path,
        )
        return ""

    update_mapping(session, mapping.id, page_id)
    return page_id
