"""Tests for services/doc-sync/main.py helpers."""

from common.models import DocType, Repository
from services_doc_sync.main import _default_doc_title


class TestDefaultDocTitle:
    def test_repository_root_title(self):
        repo = Repository(github_url="https://github.com/acme/payments-platform")
        title = _default_doc_title(
            repo=repo,
            repo_id=7,
            doc_type=DocType.architecture,
            code_path="/",
        )

        assert title == (
            "Architecture Blueprint | acme/payments-platform | Repository Overview"
        )

    def test_file_scope_title(self):
        repo = Repository(github_url="https://github.com/acme/payments-platform.git")
        title = _default_doc_title(
            repo=repo,
            repo_id=7,
            doc_type=DocType.api_reference,
            code_path="services/doc-sync/notion_provider.py",
        )

        assert title == (
            "API Reference Guide | acme/payments-platform | "
            "services/doc-sync/notion_provider.py"
        )
