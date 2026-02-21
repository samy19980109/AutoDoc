"""Tests for services/github-webhook/webhook_handler.py

Covers:
- HMAC signature validation (valid, invalid, missing, wrong algorithm)
- Push event parsing (branch pushes, tag pushes, deletions, empty commits)
- Pull request event parsing (merged only)
- Job creation and enqueueing (with mocked DB and Celery)
"""

import hashlib
import hmac
from unittest.mock import MagicMock, patch

import pytest

_WEBHOOK_SECRET = "test-webhook-secret"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signature(payload: bytes, secret: str = _WEBHOOK_SECRET) -> str:
    """Compute a valid ``X-Hub-Signature-256`` value."""
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ---------------------------------------------------------------------------
# Signature validation
# ---------------------------------------------------------------------------


class TestValidateSignature:
    """Tests for ``validate_signature``."""

    def test_valid_signature(self, patch_settings):
        from services_github_webhook.webhook_handler import validate_signature

        body = b'{"action": "push"}'
        sig = _make_signature(body)
        assert validate_signature(body, sig) is True

    def test_invalid_signature(self, patch_settings):
        from services_github_webhook.webhook_handler import validate_signature

        body = b'{"action": "push"}'
        bad_sig = "sha256=" + "0" * 64
        assert validate_signature(body, bad_sig) is False

    def test_missing_signature_header(self, patch_settings):
        from services_github_webhook.webhook_handler import validate_signature

        body = b'{"action": "push"}'
        assert validate_signature(body, "") is False

    def test_wrong_hash_algorithm_prefix(self, patch_settings):
        from services_github_webhook.webhook_handler import validate_signature

        body = b'{"action": "push"}'
        sig = "sha1=abcdef1234567890"
        assert validate_signature(body, sig) is False

    def test_no_secret_configured_skips_validation(self, mock_settings):
        """When the webhook secret is empty, validation passes unconditionally."""
        mock_settings.github_webhook_secret = ""
        with patch("services_github_webhook.webhook_handler.get_settings", return_value=mock_settings):
            from services_github_webhook.webhook_handler import validate_signature

            assert validate_signature(b"anything", "") is True


# ---------------------------------------------------------------------------
# Push event parsing
# ---------------------------------------------------------------------------


class TestParsePushEvent:
    """Tests for ``parse_push_event``."""

    def test_parses_normal_push(self, push_event_payload):
        from services_github_webhook.webhook_handler import parse_push_event

        result = parse_push_event(push_event_payload)
        assert result is not None
        assert result["repo_full_name"] == "acme/my-repo"
        assert result["repo_url"] == "https://github.com/acme/my-repo"
        assert result["branch"] == "main"
        assert result["before_sha"] == "abc123"
        assert result["after_sha"] == "def456"
        # Changed files collected from all commits, sorted
        expected = sorted({"src/new_file.py", "src/existing.py", "README.md", "old_file.py"})
        assert result["changed_files"] == expected

    def test_ignores_tag_push(self):
        from services_github_webhook.webhook_handler import parse_push_event

        payload = {"ref": "refs/tags/v1.0.0", "deleted": False, "commits": []}
        assert parse_push_event(payload) is None

    def test_ignores_branch_deletion(self):
        from services_github_webhook.webhook_handler import parse_push_event

        payload = {"ref": "refs/heads/feature-x", "deleted": True, "commits": []}
        assert parse_push_event(payload) is None

    def test_empty_commits_returns_empty_files(self):
        from services_github_webhook.webhook_handler import parse_push_event

        payload = {
            "ref": "refs/heads/main",
            "deleted": False,
            "before": "aaa",
            "after": "bbb",
            "repository": {"full_name": "org/repo", "html_url": "https://github.com/org/repo"},
            "commits": [],
        }
        result = parse_push_event(payload)
        assert result is not None
        assert result["changed_files"] == []

    def test_deduplicates_files_across_commits(self):
        from services_github_webhook.webhook_handler import parse_push_event

        payload = {
            "ref": "refs/heads/main",
            "deleted": False,
            "before": "a",
            "after": "b",
            "repository": {"full_name": "o/r", "html_url": "https://github.com/o/r"},
            "commits": [
                {"added": ["file.py"], "modified": [], "removed": []},
                {"added": [], "modified": ["file.py"], "removed": []},
            ],
        }
        result = parse_push_event(payload)
        assert result["changed_files"] == ["file.py"]


# ---------------------------------------------------------------------------
# Pull request event parsing
# ---------------------------------------------------------------------------


class TestParsePullRequestEvent:
    """Tests for ``parse_pull_request_event``."""

    def test_merged_pr(self, merged_pr_payload):
        from services_github_webhook.webhook_handler import parse_pull_request_event

        result = parse_pull_request_event(merged_pr_payload)
        assert result is not None
        assert result["repo_full_name"] == "acme/my-repo"
        assert result["repo_url"] == "https://github.com/acme/my-repo"
        assert result["pr_number"] == 42
        assert result["pr_title"] == "Add widget feature"
        assert result["merge_commit_sha"] == "aaa111bbb222"
        assert result["branch"] == "main"
        assert result["changed_files"] == []

    def test_ignores_opened_pr(self):
        from services_github_webhook.webhook_handler import parse_pull_request_event

        payload = {"action": "opened", "pull_request": {"merged": False}}
        assert parse_pull_request_event(payload) is None

    def test_ignores_closed_not_merged(self):
        from services_github_webhook.webhook_handler import parse_pull_request_event

        payload = {"action": "closed", "pull_request": {"merged": False}}
        assert parse_pull_request_event(payload) is None

    def test_ignores_synchronize_action(self):
        from services_github_webhook.webhook_handler import parse_pull_request_event

        payload = {"action": "synchronize", "pull_request": {"merged": False}}
        assert parse_pull_request_event(payload) is None

    def test_ignores_review_requested_action(self):
        from services_github_webhook.webhook_handler import parse_pull_request_event

        payload = {"action": "review_requested", "pull_request": {"merged": False}}
        assert parse_pull_request_event(payload) is None


# ---------------------------------------------------------------------------
# Job creation & enqueuing
# ---------------------------------------------------------------------------


class TestCreateAndEnqueueJob:
    """Tests for ``create_and_enqueue_job``."""

    @patch("services_github_webhook.webhook_handler._get_celery_app")
    def test_creates_job_for_existing_repo(self, mock_get_celery, mock_db, patch_settings):
        from services_github_webhook.webhook_handler import create_and_enqueue_job
        from common.models.tables import TriggerType

        # Simulate existing repository
        fake_repo = MagicMock()
        fake_repo.id = 1
        fake_repo.confluence_space_key = "ENG"
        mock_db.query.return_value.filter.return_value.first.return_value = fake_repo

        def _set_id(obj):
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = 99

        mock_db.add.side_effect = _set_id

        mock_celery = MagicMock()
        mock_get_celery.return_value = mock_celery

        job = create_and_enqueue_job(
            db=mock_db,
            repo_url="https://github.com/acme/my-repo",
            branch="main",
            changed_files=["src/app.py"],
            trigger_type=TriggerType.webhook,
        )

        assert job is not None
        mock_db.commit.assert_called_once()
        mock_celery.send_task.assert_called_once()
        assert mock_celery.send_task.call_args[0][0] == "process_documentation"

    @patch("services_github_webhook.webhook_handler._get_celery_app")
    def test_auto_registers_new_repository(self, mock_get_celery, mock_db, patch_settings):
        from services_github_webhook.webhook_handler import create_and_enqueue_job
        from common.models.tables import TriggerType

        # No existing repository
        mock_db.query.return_value.filter.return_value.first.return_value = None

        counter = {"n": 0}

        def _set_id(obj):
            counter["n"] += 1
            obj.id = counter["n"]

        mock_db.add.side_effect = _set_id

        mock_celery = MagicMock()
        mock_get_celery.return_value = mock_celery

        create_and_enqueue_job(
            db=mock_db,
            repo_url="https://github.com/acme/brand-new",
            branch="develop",
            changed_files=[],
            trigger_type=TriggerType.manual,
        )

        # Two db.add calls: one for the new Repository, one for the Job
        assert mock_db.add.call_count == 2
        mock_celery.send_task.assert_called_once()

    @patch("services_github_webhook.webhook_handler._get_celery_app")
    def test_celery_payload_contains_job_id(self, mock_get_celery, mock_db, patch_settings):
        from services_github_webhook.webhook_handler import create_and_enqueue_job
        from common.models.tables import TriggerType
        import json

        fake_repo = MagicMock()
        fake_repo.id = 5
        fake_repo.confluence_space_key = "DOC"
        mock_db.query.return_value.filter.return_value.first.return_value = fake_repo

        def _set_id(obj):
            obj.id = 77

        mock_db.add.side_effect = _set_id

        mock_celery = MagicMock()
        mock_get_celery.return_value = mock_celery

        create_and_enqueue_job(
            db=mock_db,
            repo_url="https://github.com/acme/repo",
            branch="main",
            changed_files=["a.py"],
            trigger_type=TriggerType.webhook,
        )

        # Verify the payload sent to Celery contains expected fields
        call_args = mock_celery.send_task.call_args
        payload_json = call_args[1]["args"][0] if "args" in call_args[1] else call_args[0][1][0]
        payload = json.loads(payload_json)
        assert payload["job_id"] == 77
        assert payload["repo_id"] == 5
        assert payload["branch"] == "main"
