"""Page mapping logic between code paths and destination pages."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from common.models import DocType, PageMapping

from .sync_provider import SyncProvider, get_sync_provider

logger = logging.getLogger(__name__)

_REPO_SCOPE_CODE_PATH = "/"


def get_or_create_mapping(
    session: Session,
    repo_id: int,
    code_path: str,
    doc_type: DocType,
) -> PageMapping:
    """Return an existing PageMapping or create a new one.

    Mappings are repo-scoped per doc type to keep a single destination page
    version per repository/doc type.
    """
    mappings = (
        session.query(PageMapping)
        .filter(
            PageMapping.repo_id == repo_id,
            PageMapping.doc_type == doc_type,
        )
        .all()
    )

    if mappings:
        # Prefer the canonical repo-level mapping; otherwise reuse the first
        # mapped page and normalize its key.
        mapping = next((m for m in mappings if m.code_path == _REPO_SCOPE_CODE_PATH), None)
        if mapping is None:
            mapping = next((m for m in mappings if m.destination_page_id), mappings[0])
            if mapping.code_path != _REPO_SCOPE_CODE_PATH:
                previous_code_path = mapping.code_path
                mapping.code_path = _REPO_SCOPE_CODE_PATH
                session.flush()
                logger.info(
                    "Normalized PageMapping id=%s path from '%s' to '%s'",
                    mapping.id,
                    previous_code_path,
                    _REPO_SCOPE_CODE_PATH,
                )
        return mapping

    mapping = PageMapping(
        repo_id=repo_id,
        code_path=_REPO_SCOPE_CODE_PATH,
        doc_type=doc_type,
    )
    session.add(mapping)
    session.flush()
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
    destination_page_id: str,
) -> Optional[PageMapping]:
    """Set the destination page ID and last-synced timestamp on a mapping."""
    mapping = session.query(PageMapping).filter(PageMapping.id == mapping_id).first()
    if mapping is None:
        logger.warning("PageMapping id=%s not found", mapping_id)
        return None

    mapping.destination_page_id = destination_page_id
    mapping.last_synced_at = datetime.utcnow()
    session.flush()
    logger.info(
        "Updated PageMapping id=%s -> destination_page_id=%s",
        mapping_id,
        destination_page_id,
    )
    return mapping


def sync_to_destination(
    session: Session,
    repo_id: int,
    code_path: str,
    doc_type: DocType,
    title: str,
    content: str,
    platform: str,
    config: dict,
    parent_id: Optional[str] = None,
) -> str:
    """Full sync flow: mapping lookup -> destination create/update -> mapping update.

    Parameters
    ----------
    platform:
        "confluence" or "notion"
    config:
        Platform-specific config (e.g. {"space_key": "ENG"} or {"database_id": "..."})

    Returns
    -------
    str
        The destination page ID, or empty string on failure.
    """
    mapping = get_or_create_mapping(session, repo_id, code_path, doc_type)

    provider: SyncProvider = get_sync_provider(platform)

    # If a destination page already exists, update it.
    if mapping.destination_page_id:
        existing = provider.get_page(mapping.destination_page_id)
        if existing:
            ok = provider.update_page(mapping.destination_page_id, title, content)
            if ok:
                update_mapping(session, mapping.id, mapping.destination_page_id)
                return mapping.destination_page_id
            logger.error(
                "Failed to update existing page %s; will attempt to create new page",
                mapping.destination_page_id,
            )
        else:
            logger.warning(
                "Mapped page %s no longer exists; creating a new page",
                mapping.destination_page_id,
            )

    # Create a new page.
    page_id = provider.create_page(
        config=config,
        title=title,
        content=content,
        parent_id=parent_id,
    )
    if not page_id:
        logger.error(
            "Failed to create page for repo=%s path='%s' platform=%s",
            repo_id,
            code_path,
            platform,
        )
        return ""

    update_mapping(session, mapping.id, page_id)
    return page_id
