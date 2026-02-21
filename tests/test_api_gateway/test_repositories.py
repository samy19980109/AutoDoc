"""Tests for services/api-gateway/routes/repositories.py via FastAPI TestClient."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from common.models.tables import Job, JobStatus, Repository, TriggerType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_repo(
    id_: int = 1,
    github_url: str = "https://github.com/acme/repo",
    default_branch: str = "main",
    confluence_space_key: str = "ENG",
    config_json: dict | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    m = MagicMock(spec=Repository)
    m.id = id_
    m.github_url = github_url
    m.default_branch = default_branch
    m.confluence_space_key = confluence_space_key
    m.config_json = config_json or {}
    m.created_at = created_at or datetime(2025, 1, 1, 12, 0, 0)
    return m


def _make_job(id_: int = 1, repo_id: int = 1) -> MagicMock:
    m = MagicMock(spec=Job)
    m.id = id_
    m.repo_id = repo_id
    m.trigger_type = TriggerType.manual
    m.status = JobStatus.pending
    m.started_at = None
    m.completed_at = None
    m.error = None
    return m


@pytest.fixture
def mock_db_session():
    """A mock session with chainable query support."""
    session = MagicMock()
    query = MagicMock()
    session.query.return_value = query
    query.filter.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.first.return_value = None
    query.all.return_value = []
    return session


@pytest.fixture
def client(mock_db_session):
    """Create a TestClient with DB and auth dependencies overridden."""
    mock_settings = MagicMock()
    mock_settings.celery_broker_url = "redis://localhost:6379/0"
    mock_settings.api_secret_key = "test-key"
    mock_settings.api_key_header = "X-API-Key"
    mock_settings.api_keys = ""
    mock_settings.database_url = "sqlite:///:memory:"

    with patch("common.config.settings.get_settings", return_value=mock_settings), \
         patch("common.config.get_settings", return_value=mock_settings), \
         patch("common.models.base.get_engine") as mock_engine, \
         patch("common.models.base.Base.metadata.create_all"), \
         patch("services_api_gateway.routes.repositories.celery_app") as mock_celery:

        from services_api_gateway.main import app
        from common.models import get_db
        from services_api_gateway.auth.dependencies import verify_api_key

        def _override_get_db():
            yield mock_db_session

        async def _override_verify_api_key():
            return "test-user"

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[verify_api_key] = _override_verify_api_key

        with TestClient(app, raise_server_exceptions=False) as tc:
            tc._mock_db = mock_db_session
            tc._mock_celery = mock_celery
            yield tc

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# LIST repositories
# ---------------------------------------------------------------------------


class TestListRepositories:
    def test_list_empty(self, client):
        client._mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
        resp = client.get("/api/repos/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_repos(self, client):
        repo1 = _make_repo(id_=1, github_url="https://github.com/acme/a")
        repo2 = _make_repo(id_=2, github_url="https://github.com/acme/b")
        client._mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = [
            repo1, repo2
        ]
        resp = client.get("/api/repos/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_pagination_params(self, client):
        client._mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
        resp = client.get("/api/repos/?skip=10&limit=5")
        assert resp.status_code == 200
        # Verify offset and limit were called (they're on the mock chain)
        client._mock_db.query.return_value.offset.assert_called_with(10)
        client._mock_db.query.return_value.offset.return_value.limit.assert_called_with(5)


# ---------------------------------------------------------------------------
# CREATE repository
# ---------------------------------------------------------------------------


class TestCreateRepository:
    def test_create_success(self, client):
        # No existing repo with that URL
        client._mock_db.query.return_value.filter.return_value.first.return_value = None

        def _refresh(obj):
            obj.id = 1
            obj.created_at = datetime(2025, 6, 1)

        client._mock_db.refresh.side_effect = _refresh

        resp = client.post(
            "/api/repos/",
            json={
                "github_url": "https://github.com/acme/new-repo",
                "default_branch": "main",
            },
        )
        assert resp.status_code == 201
        client._mock_db.add.assert_called_once()
        client._mock_db.commit.assert_called_once()

    def test_create_conflict(self, client):
        existing = _make_repo()
        client._mock_db.query.return_value.filter.return_value.first.return_value = existing

        resp = client.post(
            "/api/repos/",
            json={"github_url": "https://github.com/acme/repo"},
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET single repository
# ---------------------------------------------------------------------------


class TestGetRepository:
    def test_get_existing(self, client):
        repo = _make_repo(id_=1)
        client._mock_db.query.return_value.filter.return_value.first.return_value = repo

        resp = client.get("/api/repos/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["github_url"] == "https://github.com/acme/repo"

    def test_get_not_found(self, client):
        client._mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.get("/api/repos/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Repository not found"


# ---------------------------------------------------------------------------
# UPDATE repository
# ---------------------------------------------------------------------------


class TestUpdateRepository:
    def test_update_success(self, client):
        repo = _make_repo(id_=1)
        client._mock_db.query.return_value.filter.return_value.first.return_value = repo

        def _refresh(obj):
            pass

        client._mock_db.refresh.side_effect = _refresh

        resp = client.put(
            "/api/repos/1",
            json={"default_branch": "develop"},
        )
        assert resp.status_code == 200

    def test_update_not_found(self, client):
        client._mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.put("/api/repos/999", json={"default_branch": "x"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE repository
# ---------------------------------------------------------------------------


class TestDeleteRepository:
    def test_delete_success(self, client):
        repo = _make_repo(id_=1)
        client._mock_db.query.return_value.filter.return_value.first.return_value = repo

        resp = client.delete("/api/repos/1")
        assert resp.status_code == 204
        client._mock_db.delete.assert_called_once_with(repo)
        client._mock_db.commit.assert_called_once()

    def test_delete_not_found(self, client):
        client._mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.delete("/api/repos/999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TRIGGER documentation generation
# ---------------------------------------------------------------------------


class TestTriggerDocumentation:
    def test_trigger_success(self, client):
        repo = _make_repo(id_=1)
        # First call to .filter().first() finds the repo
        client._mock_db.query.return_value.filter.return_value.first.return_value = repo

        def _refresh(obj):
            obj.id = 42
            obj.repo_id = 1
            obj.trigger_type = TriggerType.manual
            obj.status = JobStatus.pending
            obj.started_at = None
            obj.completed_at = None
            obj.error = None

        client._mock_db.refresh.side_effect = _refresh

        resp = client.post("/api/repos/1/trigger")
        assert resp.status_code == 202
        client._mock_db.add.assert_called_once()
        client._mock_db.commit.assert_called_once()
        client._mock_celery.send_task.assert_called_once()

    def test_trigger_not_found(self, client):
        client._mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.post("/api/repos/999/trigger")
        assert resp.status_code == 404
