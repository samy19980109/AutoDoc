"""Abstract base class for documentation sync providers."""

from abc import ABC, abstractmethod
from typing import Optional


class SyncProvider(ABC):
    """Interface that all documentation destination providers must implement."""

    @abstractmethod
    def get_page(self, page_id: str) -> dict:
        """Fetch a page by its ID. Returns empty dict if not found."""
        ...

    @abstractmethod
    def create_page(
        self, config: dict, title: str, content: str, parent_id: Optional[str] = None
    ) -> str:
        """Create a new page. Returns the page ID, or empty string on failure."""
        ...

    @abstractmethod
    def update_page(self, page_id: str, title: str, content: str) -> bool:
        """Update an existing page. Returns True on success."""
        ...

    @abstractmethod
    def get_page_url(self, page_id: str) -> str:
        """Return the user-facing URL for a page."""
        ...

    def get_last_error(self) -> str:
        """Return the provider's most recent error message, if any."""
        return ""


def get_sync_provider(platform: str) -> SyncProvider:
    """Factory: return the correct SyncProvider for the given platform name."""
    if platform == "confluence":
        from .confluence_client import ConfluenceSyncProvider

        return ConfluenceSyncProvider()
    if platform == "notion":
        from .notion_provider import NotionSyncProvider

        return NotionSyncProvider()
    raise ValueError(f"Unsupported destination platform: {platform}")
