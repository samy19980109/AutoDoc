"""Notion API client implementing the SyncProvider interface."""

import logging
import re
from typing import Optional

from notion_client import Client as NotionClient

from common.config import get_settings

from .sync_provider import SyncProvider

logger = logging.getLogger(__name__)


def _html_to_notion_blocks(html: str) -> list[dict]:
    """Convert HTML content to Notion block objects.

    This is a pragmatic converter that handles the most common HTML elements
    produced by the doc generator (headings, paragraphs, code blocks, lists).
    """
    blocks: list[dict] = []

    # Strip tags and convert to simple text blocks.
    # For a production system you'd use a proper HTML parser; this handles
    # the AUTO-DOC output which is relatively structured.
    lines = re.sub(r"<br\s*/?>", "\n", html)

    # Convert headings (add newlines to ensure they are on separate lines)
    lines = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n### HEADING1: \1\n", lines, flags=re.DOTALL)
    lines = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n### HEADING2: \1\n", lines, flags=re.DOTALL)
    lines = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### HEADING3: \1\n", lines, flags=re.DOTALL)

    # Convert code blocks
    code_blocks = re.findall(r"<pre><code[^>]*>(.*?)</code></pre>", lines, flags=re.DOTALL)
    lines = re.sub(
        r"<pre><code[^>]*>(.*?)</code></pre>",
        "### CODEBLOCK",
        lines,
        flags=re.DOTALL,
    )

    # Strip remaining HTML tags
    lines = re.sub(r"<[^>]+>", "", lines)
    lines = lines.strip()

    code_block_idx = 0
    for line in lines.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line == "### CODEBLOCK" and code_block_idx < len(code_blocks):
            code_text = code_blocks[code_block_idx].strip()
            code_block_idx += 1
            blocks.append(
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": code_text[:2000]}}],
                        "language": "plain text",
                    },
                }
            )
        elif line.startswith("### HEADING1: "):
            text = line.removeprefix("### HEADING1: ")
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    },
                }
            )
        elif line.startswith("### HEADING2: "):
            text = line.removeprefix("### HEADING2: ")
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    },
                }
            )
        elif line.startswith("### HEADING3: "):
            text = line.removeprefix("### HEADING3: ")
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    },
                }
            )
        else:
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line[:2000]}}]
                    },
                }
            )

    return blocks


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
