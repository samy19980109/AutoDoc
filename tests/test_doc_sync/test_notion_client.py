"""Tests for services/doc-sync/notion_provider.py"""

from unittest.mock import MagicMock, patch

import pytest

# Pre-import to ensure the module is in sys.modules for patching
import services_doc_sync.notion_provider as _notion_mod


# ---------------------------------------------------------------------------
# HTML → Notion block conversion
# ---------------------------------------------------------------------------


class TestHtmlToNotionBlocks:
    def test_converts_paragraph(self):
        from services_doc_sync.notion_provider import _html_to_notion_blocks

        blocks = _html_to_notion_blocks("<p>Hello world</p>")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        assert blocks[0]["paragraph"]["rich_text"][0]["text"]["content"] == "Hello world"

    def test_converts_headings(self):
        from services_doc_sync.notion_provider import _html_to_notion_blocks

        html = "<h1>Title</h1><h2>Subtitle</h2><h3>Section</h3>"
        blocks = _html_to_notion_blocks(html)

        types = [b["type"] for b in blocks]
        assert "heading_1" in types
        assert "heading_2" in types
        assert "heading_3" in types

    def test_converts_code_block(self):
        from services_doc_sync.notion_provider import _html_to_notion_blocks

        html = "<pre><code>def foo():\n    pass</code></pre>"
        blocks = _html_to_notion_blocks(html)

        code_blocks = [b for b in blocks if b["type"] == "code"]
        assert len(code_blocks) == 1
        assert "def foo():" in code_blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_empty_html(self):
        from services_doc_sync.notion_provider import _html_to_notion_blocks

        blocks = _html_to_notion_blocks("")
        assert blocks == []

    def test_converts_lists_quotes_and_dividers(self):
        from services_doc_sync.notion_provider import _html_to_notion_blocks

        html = (
            "<ul><li>alpha</li><li>beta</li></ul>"
            "<ol><li>one</li></ol>"
            "<blockquote>Key decision</blockquote>"
            "<hr />"
        )
        blocks = _html_to_notion_blocks(html)
        types = [b["type"] for b in blocks]

        assert "bulleted_list_item" in types
        assert "numbered_list_item" in types
        assert "quote" in types
        assert "divider" in types


# ---------------------------------------------------------------------------
# NotionSyncProvider
# ---------------------------------------------------------------------------


class TestNotionSyncProvider:
    @patch("services_doc_sync.notion_provider.NotionClient")
    def test_get_page_success(self, MockClient, patch_settings):
        from services_doc_sync.notion_provider import NotionSyncProvider

        client = MagicMock()
        MockClient.return_value = client
        client.pages.retrieve.return_value = {"id": "page-123", "properties": {}}

        provider = NotionSyncProvider()
        result = provider.get_page("page-123")

        assert result["id"] == "page-123"
        client.pages.retrieve.assert_called_once_with(page_id="page-123")

    @patch("services_doc_sync.notion_provider.NotionClient")
    def test_get_page_not_found(self, MockClient, patch_settings):
        from services_doc_sync.notion_provider import NotionSyncProvider

        client = MagicMock()
        MockClient.return_value = client
        client.pages.retrieve.side_effect = Exception("Not found")

        provider = NotionSyncProvider()
        result = provider.get_page("bad-id")

        assert result == {}
        assert provider.get_last_error()

    @patch("services_doc_sync.notion_provider.NotionClient")
    def test_create_page_with_database(self, MockClient, patch_settings):
        from services_doc_sync.notion_provider import NotionSyncProvider

        client = MagicMock()
        MockClient.return_value = client
        client.databases.retrieve.return_value = {
            "properties": {
                "Name": {"type": "title"},
                "Status": {"type": "select"},
            }
        }
        client.pages.create.return_value = {"id": "new-page-456"}

        provider = NotionSyncProvider()
        page_id = provider.create_page(
            config={"database_id": "db-abc"},
            title="Test Doc",
            content="<p>Content</p>",
        )

        assert page_id == "new-page-456"
        call_kwargs = client.pages.create.call_args[1]
        assert call_kwargs["parent"] == {"database_id": "db-abc"}
        assert call_kwargs["properties"]["Name"]["title"][0]["text"]["content"] == "Test Doc"

    @patch("services_doc_sync.notion_provider.NotionClient")
    def test_create_page_with_page_parent_uses_title_property(self, MockClient, patch_settings):
        from services_doc_sync.notion_provider import NotionSyncProvider

        client = MagicMock()
        MockClient.return_value = client
        client.pages.create.return_value = {"id": "new-page-789"}

        provider = NotionSyncProvider()
        page_id = provider.create_page(
            config={"page_id": "parent-123"},
            title="Page Parent",
            content="<p>Content</p>",
        )

        assert page_id == "new-page-789"
        call_kwargs = client.pages.create.call_args[1]
        assert call_kwargs["parent"] == {"page_id": "parent-123"}
        assert call_kwargs["properties"]["title"]["title"][0]["text"]["content"] == "Page Parent"

    @patch("services_doc_sync.notion_provider.NotionClient")
    def test_create_page_with_empty_content_adds_fallback_paragraph(self, MockClient, patch_settings):
        from services_doc_sync.notion_provider import NotionSyncProvider

        client = MagicMock()
        MockClient.return_value = client
        client.pages.create.return_value = {"id": "new-page-111"}

        provider = NotionSyncProvider()
        page_id = provider.create_page(
            config={"page_id": "parent-123"},
            title="Fallback Content",
            content="   ",
        )

        assert page_id == "new-page-111"
        call_kwargs = client.pages.create.call_args[1]
        assert call_kwargs["children"][0]["type"] == "paragraph"

    @patch("services_doc_sync.notion_provider.NotionClient")
    def test_create_page_failure(self, MockClient, patch_settings):
        from services_doc_sync.notion_provider import NotionSyncProvider

        client = MagicMock()
        MockClient.return_value = client
        client.pages.create.side_effect = Exception("API error")

        provider = NotionSyncProvider()
        page_id = provider.create_page(
            config={"database_id": "db-abc"},
            title="Test",
            content="<p>X</p>",
        )

        assert page_id == ""
        assert provider.get_last_error()

    @patch("services_doc_sync.notion_provider.NotionClient")
    def test_update_page_success(self, MockClient, patch_settings):
        from services_doc_sync.notion_provider import NotionSyncProvider

        client = MagicMock()
        MockClient.return_value = client
        client.blocks.children.list.return_value = {"results": []}

        provider = NotionSyncProvider()
        ok = provider.update_page("page-123", "Updated Title", "<p>New content</p>")

        assert ok is True
        client.pages.update.assert_called_once()
        client.blocks.children.append.assert_called_once()

    @patch("services_doc_sync.notion_provider.NotionClient")
    def test_update_page_failure(self, MockClient, patch_settings):
        from services_doc_sync.notion_provider import NotionSyncProvider

        client = MagicMock()
        MockClient.return_value = client
        client.pages.update.side_effect = Exception("API error")

        provider = NotionSyncProvider()
        ok = provider.update_page("page-123", "Title", "<p>X</p>")

        assert ok is False
        assert provider.get_last_error()

    @patch("services_doc_sync.notion_provider.NotionClient")
    def test_get_page_url(self, MockClient, patch_settings):
        from services_doc_sync.notion_provider import NotionSyncProvider

        provider = NotionSyncProvider()
        url = provider.get_page_url("abc-def-123")

        assert url == "https://www.notion.so/abcdef123"
