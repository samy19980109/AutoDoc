"""Tests for services/doc-sync/page_mapper.py (generalized sync)"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from common.models.tables import DocType, PageMapping


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mapping(
    id_: int = 1,
    repo_id: int = 10,
    code_path: str = "src/main.py",
    doc_type: DocType = DocType.api_reference,
    destination_page_id: str | None = None,
    last_synced_at: datetime | None = None,
) -> MagicMock:
    """Create a MagicMock that looks like a PageMapping row."""
    m = MagicMock(spec=PageMapping)
    m.id = id_
    m.repo_id = repo_id
    m.code_path = code_path
    m.doc_type = doc_type
    m.destination_page_id = destination_page_id
    m.last_synced_at = last_synced_at
    return m


# ---------------------------------------------------------------------------
# get_or_create_mapping
# ---------------------------------------------------------------------------


class TestGetOrCreateMapping:
    def test_returns_existing_mapping(self, mock_db):
        from services_doc_sync.page_mapper import get_or_create_mapping

        existing = _make_mapping(id_=5)
        mock_db.query.return_value.filter.return_value.all.return_value = [existing]

        result = get_or_create_mapping(
            mock_db, repo_id=10, code_path="src/main.py", doc_type=DocType.api_reference
        )

        assert result is existing
        mock_db.add.assert_not_called()

    def test_creates_new_mapping_when_none_exists(self, mock_db):
        from services_doc_sync.page_mapper import get_or_create_mapping

        mock_db.query.return_value.filter.return_value.all.return_value = []

        def _flush():
            pass

        mock_db.flush.side_effect = _flush

        result = get_or_create_mapping(
            mock_db, repo_id=10, code_path="src/new.py", doc_type=DocType.architecture
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert isinstance(added_obj, PageMapping)
        assert added_obj.repo_id == 10
        assert added_obj.code_path == "/"
        assert added_obj.doc_type == DocType.architecture

    def test_reuses_existing_repo_mapping_with_different_code_path(self, mock_db):
        from services_doc_sync.page_mapper import get_or_create_mapping

        existing = _make_mapping(
            id_=9,
            code_path="src/legacy.py",
            doc_type=DocType.architecture,
            destination_page_id="PAGE-9",
        )
        mock_db.query.return_value.filter.return_value.all.return_value = [existing]

        result = get_or_create_mapping(
            mock_db, repo_id=10, code_path="src/new.py", doc_type=DocType.architecture
        )

        assert result is existing
        assert existing.code_path == "/"
        mock_db.add.assert_not_called()


# ---------------------------------------------------------------------------
# update_mapping
# ---------------------------------------------------------------------------


class TestUpdateMapping:
    def test_updates_existing_mapping(self, mock_db):
        from services_doc_sync.page_mapper import update_mapping

        existing = _make_mapping(id_=7, destination_page_id=None)
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        result = update_mapping(mock_db, mapping_id=7, destination_page_id="12345")

        assert result is existing
        assert existing.destination_page_id == "12345"
        assert existing.last_synced_at is not None
        mock_db.flush.assert_called_once()

    def test_returns_none_when_not_found(self, mock_db):
        from services_doc_sync.page_mapper import update_mapping

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = update_mapping(mock_db, mapping_id=999, destination_page_id="12345")
        assert result is None


# ---------------------------------------------------------------------------
# sync_to_destination
# ---------------------------------------------------------------------------


class TestSyncToDestination:
    """Tests for the full sync_to_destination flow."""

    @patch("services_doc_sync.page_mapper.get_sync_provider")
    @patch("services_doc_sync.page_mapper.get_or_create_mapping")
    @patch("services_doc_sync.page_mapper.update_mapping")
    def test_creates_new_page_when_no_existing(
        self, mock_update, mock_get_or_create, mock_get_provider, mock_db
    ):
        from services_doc_sync.page_mapper import sync_to_destination

        mapping = _make_mapping(id_=1, destination_page_id=None)
        mock_get_or_create.return_value = mapping

        provider_instance = MagicMock()
        mock_get_provider.return_value = provider_instance
        provider_instance.create_page.return_value = "NEW-PAGE-123"

        page_id = sync_to_destination(
            session=mock_db,
            repo_id=10,
            code_path="src/main.py",
            doc_type=DocType.api_reference,
            title="API Reference",
            content="<p>Docs</p>",
            platform="confluence",
            config={"space_key": "ENG"},
        )

        assert page_id == "NEW-PAGE-123"
        provider_instance.create_page.assert_called_once_with(
            config={"space_key": "ENG"},
            title="API Reference",
            content="<p>Docs</p>",
            parent_id=None,
        )
        mock_update.assert_called_once_with(mock_db, 1, "NEW-PAGE-123")

    @patch("services_doc_sync.page_mapper.get_sync_provider")
    @patch("services_doc_sync.page_mapper.get_or_create_mapping")
    @patch("services_doc_sync.page_mapper.update_mapping")
    def test_updates_existing_page(
        self, mock_update, mock_get_or_create, mock_get_provider, mock_db
    ):
        from services_doc_sync.page_mapper import sync_to_destination

        mapping = _make_mapping(id_=2, destination_page_id="EXISTING-456")
        mock_get_or_create.return_value = mapping

        provider_instance = MagicMock()
        mock_get_provider.return_value = provider_instance
        provider_instance.get_page.return_value = {"id": "EXISTING-456"}
        provider_instance.update_page.return_value = True

        page_id = sync_to_destination(
            session=mock_db,
            repo_id=10,
            code_path="src/main.py",
            doc_type=DocType.api_reference,
            title="API Reference v2",
            content="<p>Updated</p>",
            platform="confluence",
            config={"space_key": "ENG"},
        )

        assert page_id == "EXISTING-456"
        provider_instance.update_page.assert_called_once_with(
            "EXISTING-456", "API Reference v2", "<p>Updated</p>"
        )

    @patch("services_doc_sync.page_mapper.get_sync_provider")
    @patch("services_doc_sync.page_mapper.get_or_create_mapping")
    @patch("services_doc_sync.page_mapper.update_mapping")
    def test_creates_page_when_mapped_page_deleted(
        self, mock_update, mock_get_or_create, mock_get_provider, mock_db
    ):
        """If the destination page was deleted externally, create a new one."""
        from services_doc_sync.page_mapper import sync_to_destination

        mapping = _make_mapping(id_=3, destination_page_id="GONE-789")
        mock_get_or_create.return_value = mapping

        provider_instance = MagicMock()
        mock_get_provider.return_value = provider_instance
        provider_instance.get_page.return_value = {}
        provider_instance.create_page.return_value = "RECREATED-001"

        page_id = sync_to_destination(
            session=mock_db,
            repo_id=10,
            code_path="src/gone.py",
            doc_type=DocType.walkthrough,
            title="Walkthrough",
            content="<p>Walk</p>",
            platform="notion",
            config={"database_id": "abc123"},
        )

        assert page_id == "RECREATED-001"
        provider_instance.create_page.assert_called_once()

    @patch("services_doc_sync.page_mapper.get_sync_provider")
    @patch("services_doc_sync.page_mapper.get_or_create_mapping")
    def test_raises_runtime_error_on_create_failure(
        self, mock_get_or_create, mock_get_provider, mock_db
    ):
        from services_doc_sync.page_mapper import sync_to_destination

        mapping = _make_mapping(id_=4, destination_page_id=None)
        mock_get_or_create.return_value = mapping

        provider_instance = MagicMock()
        mock_get_provider.return_value = provider_instance
        provider_instance.create_page.return_value = ""
        provider_instance.get_last_error.return_value = "Notion auth failed"

        with pytest.raises(RuntimeError, match="Notion auth failed"):
            sync_to_destination(
                session=mock_db,
                repo_id=10,
                code_path="src/fail.py",
                doc_type=DocType.api_reference,
                title="Fail",
                content="<p>X</p>",
                platform="confluence",
                config={"space_key": "ENG"},
            )
