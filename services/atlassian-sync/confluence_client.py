"""Confluence API client for creating and managing documentation pages."""

import logging
from typing import Optional

from atlassian import Confluence
from atlassian.errors import ApiError

from common.config import get_settings

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Wraps atlassian-python-api Confluence to manage documentation pages."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = Confluence(
            url=settings.confluence_url,
            username=settings.confluence_username,
            password=settings.confluence_api_token,
            cloud=True,
        )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_page(self, page_id: str) -> dict:
        """Return the full page representation for *page_id*.

        Returns an empty dict when the page cannot be found or the API
        returns an error.
        """
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

    def get_child_pages(self, page_id: str) -> list[dict]:
        """Return a list of direct child pages under *page_id*."""
        try:
            children = self._client.get_page_child_by_type(
                page_id,
                type="page",
                start=0,
                limit=250,
            )
            return children
        except ApiError as exc:
            logger.error("Failed to get children for page %s: %s", page_id, exc)
            return []
        except Exception as exc:
            logger.error(
                "Unexpected error getting children for page %s: %s", page_id, exc
            )
            return []

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_id: Optional[str] = None,
    ) -> str:
        """Create a new Confluence page and return its page ID.

        Parameters
        ----------
        space_key:
            The Confluence space key (e.g. ``ENG``).
        title:
            Page title.  Must be unique within the space.
        body:
            Page body in Confluence *storage* format (XHTML).
        parent_id:
            Optional parent page ID to nest this page under.

        Returns
        -------
        str
            The newly created page's ID, or an empty string on failure.
        """
        try:
            result = self._client.create_page(
                space=space_key,
                title=title,
                body=body,
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

    def update_page(self, page_id: str, title: str, body: str) -> bool:
        """Update an existing Confluence page's title and body.

        Returns ``True`` on success, ``False`` otherwise.
        """
        try:
            self._client.update_page(
                page_id=page_id,
                title=title,
                body=body,
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
