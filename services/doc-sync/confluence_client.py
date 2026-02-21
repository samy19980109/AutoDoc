"""Confluence API client implementing the SyncProvider interface."""

import logging
from typing import Optional

from atlassian import Confluence
from atlassian.errors import ApiError

from common.config import get_settings

from .sync_provider import SyncProvider

logger = logging.getLogger(__name__)


class ConfluenceSyncProvider(SyncProvider):
    """Wraps atlassian-python-api Confluence to implement SyncProvider."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = Confluence(
            url=settings.confluence_url,
            username=settings.confluence_username,
            password=settings.confluence_api_token,
            cloud=True,
        )
        self._base_url = settings.confluence_url

    def get_page(self, page_id: str) -> dict:
        try:
            page = self._client.get_page_by_id(
                page_id,
                expand="body.storage,version",
            )
            return page
        except ApiError as exc:
            logger.error("Failed to get page %s: %s", page_id, exc)
            return {}
        except Exception as exc:
            logger.error("Unexpected error getting page %s: %s", page_id, exc)
            return {}

    def create_page(
        self, config: dict, title: str, content: str, parent_id: Optional[str] = None
    ) -> str:
        """Create a Confluence page.

        ``config`` should contain ``space_key``.
        """
        space_key = config.get("space_key", "")
        if not space_key:
            logger.error("No space_key in config for Confluence page creation")
            return ""

        try:
            result = self._client.create_page(
                space=space_key,
                title=title,
                body=content,
                parent_id=parent_id,
                type="page",
                representation="storage",
            )
            page_id = str(result.get("id", ""))
            logger.info(
                "Created Confluence page '%s' (id=%s) in space %s",
                title,
                page_id,
                space_key,
            )
            return page_id
        except ApiError as exc:
            logger.error(
                "Failed to create page '%s' in space %s: %s", title, space_key, exc
            )
            return ""
        except Exception as exc:
            logger.error(
                "Unexpected error creating page '%s' in space %s: %s",
                title,
                space_key,
                exc,
            )
            return ""

    def update_page(self, page_id: str, title: str, content: str) -> bool:
        try:
            self._client.update_page(
                page_id=page_id,
                title=title,
                body=content,
                representation="storage",
            )
            logger.info("Updated Confluence page %s ('%s')", page_id, title)
            return True
        except ApiError as exc:
            logger.error("Failed to update page %s: %s", page_id, exc)
            return False
        except Exception as exc:
            logger.error("Unexpected error updating page %s: %s", page_id, exc)
            return False

    def get_page_url(self, page_id: str) -> str:
        return f"{self._base_url.rstrip('/')}/pages/{page_id}"

    # Legacy convenience methods for direct usage
    def get_child_pages(self, page_id: str) -> list[dict]:
        try:
            children = self._client.get_page_child_by_type(
                page_id,
                type="page",
                start=0,
                limit=250,
            )
            return children
        except Exception as exc:
            logger.error("Failed to get children for page %s: %s", page_id, exc)
            return []
