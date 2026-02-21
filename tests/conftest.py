"""Shared test fixtures for the enterprise auto-documentation test suite.

The service directories use dashes in their names (e.g. ``github-webhook``),
which are not valid Python identifiers.  This conftest adds the project root
to ``sys.path`` and registers the dash-named directories as importable
packages under underscore-based aliases so that test modules can write::

    from services_github_webhook.webhook_handler import validate_signature
"""

from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Make dash-named service directories importable with underscore names
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ensure project root is on sys.path so ``common`` is importable.
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_SERVICE_DIR = _PROJECT_ROOT / "services"

# Map underscore module names to their actual dash-named directories.
_SERVICE_MAP = {
    "services_github_webhook": _SERVICE_DIR / "github-webhook",
    "services_doc_processor": _SERVICE_DIR / "doc-processor",
    "services_atlassian_sync": _SERVICE_DIR / "atlassian-sync",
    "services_doc_sync": _SERVICE_DIR / "doc-sync",
    "services_api_gateway": _SERVICE_DIR / "api-gateway",
}

for mod_name, dir_path in _SERVICE_MAP.items():
    if mod_name not in sys.modules:
        # Create a package module pointing at the directory
        spec = importlib.util.spec_from_file_location(
            mod_name,
            dir_path / "__init__.py",
            submodule_search_locations=[str(dir_path)],
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
        else:
            # Fallback: create an empty namespace package
            mod = types.ModuleType(mod_name)
            mod.__path__ = [str(dir_path)]
            sys.modules[mod_name] = mod

# Also add each service dir to sys.path so intra-service imports
# (e.g. ``from prompts import ...`` inside doc-processor) work.
for dir_path in _SERVICE_MAP.values():
    _dir_str = str(dir_path)
    if _dir_str not in sys.path:
        sys.path.insert(0, _dir_str)


# ---------------------------------------------------------------------------
# Mock Settings
# ---------------------------------------------------------------------------


class _MockSettings:
    """Minimal settings object used across all test modules."""

    database_url: str = "sqlite:///:memory:"
    redis_url: str = "redis://localhost:6379/0"
    github_webhook_secret: str = "test-webhook-secret"
    github_token: str = "ghp_test_token"
    ai_provider: str = "anthropic"
    anthropic_api_key: str = "sk-ant-test"
    openai_api_key: str = ""
    ai_model: str = "claude-sonnet-4-20250514"
    confluence_url: str = "https://test.atlassian.net/wiki"
    confluence_username: str = "test@example.com"
    confluence_api_token: str = "confluence-token"
    jira_url: str = "https://test.atlassian.net"
    jira_username: str = "test@example.com"
    jira_api_token: str = "jira-token"
    notion_api_key: str = "ntn_test_key"
    doc_sync_url: str = "http://localhost:8002"
    api_secret_key: str = "test-secret-key"
    api_key_header: str = "X-API-Key"
    api_keys: str = "test-key-1,test-key-2"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"


@pytest.fixture
def mock_settings():
    """Return a mock Settings instance with test values."""
    return _MockSettings()


@pytest.fixture
def patch_settings(mock_settings):
    """Patch ``get_settings`` globally to return mock settings."""
    with patch("common.config.get_settings", return_value=mock_settings), \
         patch("common.config.settings.get_settings", return_value=mock_settings):
        yield mock_settings


# ---------------------------------------------------------------------------
# Mock DB Session
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Provide a MagicMock that behaves like a SQLAlchemy Session.

    The mock supports chaining: ``session.query(...).filter(...).first()``
    """
    session = MagicMock()

    # Make .query().filter().first() chainable by default.
    query_mock = MagicMock()
    session.query.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.offset.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.first.return_value = None
    query_mock.all.return_value = []

    return session


# ---------------------------------------------------------------------------
# Mock Celery
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_celery():
    """Return a MagicMock acting as a Celery application."""
    celery = MagicMock()
    celery.send_task = MagicMock()
    return celery


# ---------------------------------------------------------------------------
# Sample GitHub payloads
# ---------------------------------------------------------------------------


@pytest.fixture
def push_event_payload():
    """A realistic GitHub push event payload."""
    return {
        "ref": "refs/heads/main",
        "before": "abc123",
        "after": "def456",
        "deleted": False,
        "repository": {
            "full_name": "acme/my-repo",
            "html_url": "https://github.com/acme/my-repo",
        },
        "commits": [
            {
                "added": ["src/new_file.py"],
                "modified": ["src/existing.py"],
                "removed": [],
            },
            {
                "added": [],
                "modified": ["README.md"],
                "removed": ["old_file.py"],
            },
        ],
    }


@pytest.fixture
def merged_pr_payload():
    """A realistic GitHub pull_request event payload for a merged PR."""
    return {
        "action": "closed",
        "pull_request": {
            "merged": True,
            "number": 42,
            "title": "Add widget feature",
            "merge_commit_sha": "aaa111bbb222",
            "base": {"ref": "main"},
        },
        "repository": {
            "full_name": "acme/my-repo",
            "html_url": "https://github.com/acme/my-repo",
        },
    }
