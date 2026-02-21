"""Notion API client implementing the SyncProvider interface."""

import logging
from html import unescape
from html.parser import HTMLParser
from typing import Optional

from notion_client import Client as NotionClient

from common.config import get_settings

from .sync_provider import SyncProvider

logger = logging.getLogger(__name__)


def _plain_rich_text(content: str) -> list[dict]:
    return [{"type": "text", "text": {"content": content[:2000]}}]


class _NotionHTMLParser(HTMLParser):
    """Minimal HTML parser that maps common documentation tags to Notion blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self._current_text: list[str] = []
        self._current_block_kind: str = "paragraph"
        self._list_stack: list[str] = []
        self._in_pre = False
        self._in_code = False

    def _push_text_block(self, kind: Optional[str] = None) -> None:
        text = unescape("".join(self._current_text)).strip()
        self._current_text = []
        if not text:
            return

        block_kind = kind or self._current_block_kind
        if block_kind == "heading_1":
            self.blocks.append(
                {"object": "block", "type": "heading_1", "heading_1": {"rich_text": _plain_rich_text(text)}}
            )
        elif block_kind == "heading_2":
            self.blocks.append(
                {"object": "block", "type": "heading_2", "heading_2": {"rich_text": _plain_rich_text(text)}}
            )
        elif block_kind == "heading_3":
            self.blocks.append(
                {"object": "block", "type": "heading_3", "heading_3": {"rich_text": _plain_rich_text(text)}}
            )
        elif block_kind == "quote":
            self.blocks.append(
                {"object": "block", "type": "quote", "quote": {"rich_text": _plain_rich_text(text)}}
            )
        elif block_kind == "code":
            self.blocks.append(
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": _plain_rich_text(text),
                        "language": "plain text",
                    },
                }
            )
        elif block_kind == "bulleted_list_item":
            self.blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": _plain_rich_text(text)},
                }
            )
        elif block_kind == "numbered_list_item":
            self.blocks.append(
                {
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {"rich_text": _plain_rich_text(text)},
                }
            )
        else:
            self.blocks.append(
                {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _plain_rich_text(text)}}
            )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "p", "li", "blockquote", "pre"}:
            self._push_text_block()

        if tag == "h1":
            self._current_block_kind = "heading_1"
        elif tag == "h2":
            self._current_block_kind = "heading_2"
        elif tag == "h3":
            self._current_block_kind = "heading_3"
        elif tag == "blockquote":
            self._current_block_kind = "quote"
        elif tag == "pre":
            self._current_block_kind = "code"
            self._in_pre = True
        elif tag == "code":
            self._in_code = True
            if not self._in_pre:
                self._current_text.append("`")
        elif tag == "ul":
            self._list_stack.append("bulleted_list_item")
        elif tag == "ol":
            self._list_stack.append("numbered_list_item")
        elif tag == "li":
            if self._list_stack:
                self._current_block_kind = self._list_stack[-1]
            else:
                self._current_block_kind = "paragraph"
        elif tag == "br":
            self._current_text.append("\n")
        elif tag == "hr":
            self._push_text_block()
            self.blocks.append({"object": "block", "type": "divider", "divider": {}})

    def handle_endtag(self, tag: str) -> None:
        if tag == "code":
            self._in_code = False
            if not self._in_pre:
                self._current_text.append("`")

        if tag in {"h1", "h2", "h3", "p", "li", "blockquote", "pre"}:
            self._push_text_block()
            self._current_block_kind = "paragraph"

        if tag in {"ul", "ol"} and self._list_stack:
            self._list_stack.pop()

        if tag == "pre":
            self._in_pre = False

    def handle_data(self, data: str) -> None:
        if not data:
            return
        self._current_text.append(data)


def _html_to_notion_blocks(html: str) -> list[dict]:
    """Convert HTML content to Notion block objects.

    Handles common documentation HTML (headings, paragraphs, lists, quotes,
    dividers, and code blocks).
    """
    if not html or not html.strip():
        return []

    parser = _NotionHTMLParser()
    parser.feed(html)
    parser.close()
    parser._push_text_block()

    return parser.blocks


class NotionSyncProvider(SyncProvider):
    """Wraps the official Notion SDK to implement SyncProvider."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = NotionClient(auth=settings.notion_api_key)

    def get_page(self, page_id: str) -> dict:
        try:
            page = self._client.pages.retrieve(page_id=page_id)
            return page
        except Exception as exc:
            logger.error("Failed to get Notion page %s: %s", page_id, exc)
            return {}

    def create_page(
        self, config: dict, title: str, content: str, parent_id: Optional[str] = None
    ) -> str:
        """Create a Notion page.

        ``config`` should contain ``database_id`` for creating pages inside a
        Notion database, or ``parent_page_id`` for nesting under another page.
        """
        try:
            blocks = _html_to_notion_blocks(content)

            # Determine parent: database, page from config, or explicit parent_id
            parent: dict
            database_id = config.get("database_id")
            parent_page_id = config.get("page_id") or parent_id
            if database_id:
                parent = {"database_id": database_id}
            elif parent_page_id:
                parent = {"page_id": parent_page_id}
            else:
                raise ValueError(
                    "Notion config must include 'database_id' or 'page_id'"
                )

            properties: dict = {"title": {"title": [{"text": {"content": title}}]}}

            result = self._client.pages.create(
                parent=parent,
                properties=properties,
                children=blocks,
            )

            page_id = result["id"]
            logger.info("Created Notion page '%s' (id=%s)", title, page_id)
            return page_id

        except Exception as exc:
            logger.error("Failed to create Notion page '%s': %s", title, exc)
            return ""

    def update_page(self, page_id: str, title: str, content: str) -> bool:
        try:
            # Update title
            self._client.pages.update(
                page_id=page_id,
                properties={"title": {"title": [{"text": {"content": title}}]}},
            )

            # Delete existing children, then append new blocks.
            # Notion API requires fetching existing block children first.
            existing_children = self._client.blocks.children.list(block_id=page_id)
            for block in existing_children.get("results", []):
                try:
                    self._client.blocks.delete(block_id=block["id"])
                except Exception:
                    pass  # Best effort cleanup

            blocks = _html_to_notion_blocks(content)
            if blocks:
                self._client.blocks.children.append(block_id=page_id, children=blocks)

            logger.info("Updated Notion page %s ('%s')", page_id, title)
            return True

        except Exception as exc:
            logger.error("Failed to update Notion page %s: %s", page_id, exc)
            return False

    def get_page_url(self, page_id: str) -> str:
        # Notion page URLs follow this pattern
        clean_id = page_id.replace("-", "")
        return f"https://www.notion.so/{clean_id}"
