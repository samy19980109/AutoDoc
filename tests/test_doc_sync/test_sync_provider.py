"""Tests for services/doc-sync/sync_provider.py — factory and routing."""

import pytest
from unittest.mock import patch

# Pre-import to ensure modules are in sys.modules for patching
import services_doc_sync.sync_provider as _sp_mod
import services_doc_sync.confluence_client as _cc_mod
import services_doc_sync.notion_provider as _nc_mod


class TestGetSyncProvider:
    def test_returns_confluence_provider(self, patch_settings):
        from services_doc_sync.sync_provider import get_sync_provider
        from services_doc_sync.confluence_client import ConfluenceSyncProvider

        with patch.object(ConfluenceSyncProvider, "__init__", return_value=None):
            provider = get_sync_provider("confluence")
            assert isinstance(provider, ConfluenceSyncProvider)

    def test_returns_notion_provider(self, patch_settings):
        from services_doc_sync.sync_provider import get_sync_provider
        from services_doc_sync.notion_provider import NotionSyncProvider

        with patch.object(NotionSyncProvider, "__init__", return_value=None):
            provider = get_sync_provider("notion")
            assert isinstance(provider, NotionSyncProvider)

    def test_raises_for_unknown_platform(self):
        from services_doc_sync.sync_provider import get_sync_provider

        with pytest.raises(ValueError, match="Unsupported destination platform"):
            get_sync_provider("gitbook")
