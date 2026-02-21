"""Fetch repository metadata and file contents via the GitHub API (PyGithub)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from github import Github, GithubException

from common.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RepoInfo:
    full_name: str
    default_branch: str
    clone_url: str
    html_url: str
    description: Optional[str]


@dataclass(frozen=True)
class FileContent:
    path: str
    content: str  # decoded text content
    sha: str
    size: int


def _get_github_client() -> Github:
    settings = get_settings()
    if not settings.github_token:
        raise RuntimeError("AUTODOC_GITHUB_TOKEN is not configured")
    return Github(settings.github_token)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_repo_info(repo_full_name: str) -> RepoInfo:
    """Return basic metadata for a GitHub repository.

    Args:
        repo_full_name: ``"owner/repo"`` style identifier.
    """
    gh = _get_github_client()
    try:
        repo = gh.get_repo(repo_full_name)
    except GithubException as exc:
        logger.error("Failed to fetch repo %s: %s", repo_full_name, exc)
        raise

    return RepoInfo(
        full_name=repo.full_name,
        default_branch=repo.default_branch,
        clone_url=repo.clone_url,
        html_url=repo.html_url,
        description=repo.description,
    )


def fetch_file_contents(
    repo_full_name: str,
    paths: list[str],
    ref: Optional[str] = None,
) -> list[FileContent]:
    """Fetch decoded file contents for a list of paths.

    Files that cannot be retrieved (deleted, binary, too large) are silently
    skipped and a warning is logged.

    Args:
        repo_full_name: ``"owner/repo"``.
        paths: File paths relative to the repository root.
        ref: Git ref (branch, tag, SHA). Defaults to the repo's default branch.
    """
    gh = _get_github_client()
    repo = gh.get_repo(repo_full_name)

    results: list[FileContent] = []
    for path in paths:
        try:
            kwargs = {"path": path}
            if ref:
                kwargs["ref"] = ref
            content_file = repo.get_contents(**kwargs)

            # get_contents can return a list for directories -- skip those.
            if isinstance(content_file, list):
                logger.warning("Path %s is a directory, skipping", path)
                continue

            decoded = content_file.decoded_content.decode("utf-8", errors="replace")
            results.append(
                FileContent(
                    path=content_file.path,
                    content=decoded,
                    sha=content_file.sha,
                    size=content_file.size,
                )
            )
        except GithubException as exc:
            logger.warning("Could not fetch %s from %s: %s", path, repo_full_name, exc)
        except UnicodeDecodeError:
            logger.warning("Binary file skipped: %s", path)

    return results


def get_changed_files_between_commits(
    repo_full_name: str,
    base_sha: str,
    head_sha: str,
) -> list[str]:
    """Return the list of file paths changed between two commits.

    Uses the GitHub Compare API so it works even for force-pushes where the
    base commit is no longer an ancestor.
    """
    gh = _get_github_client()
    repo = gh.get_repo(repo_full_name)

    try:
        comparison = repo.compare(base_sha, head_sha)
        return [f.filename for f in comparison.files]
    except GithubException as exc:
        logger.error(
            "Failed to compare %s..%s in %s: %s",
            base_sha,
            head_sha,
            repo_full_name,
            exc,
        )
        raise
