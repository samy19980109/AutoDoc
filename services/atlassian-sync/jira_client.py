"""JIRA API client for searching tickets and adding documentation links."""

import logging

from atlassian import Jira
from atlassian.errors import ApiError

from common.config import get_settings

logger = logging.getLogger(__name__)


class JiraClient:
    """Wraps atlassian-python-api Jira to manage ticket interactions."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = Jira(
            url=settings.jira_url,
            username=settings.jira_username,
            password=settings.jira_api_token,
            cloud=True,
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_tickets(self, query: str) -> list[dict]:
        """Execute a JQL query and return matching issues.

        Parameters
        ----------
        query:
            A valid JQL string, e.g. ``'project = ENG AND summary ~ "auth"'``.

        Returns
        -------
        list[dict]
            A list of issue dicts (key, summary, status, assignee).
        """
        try:
            results = self._client.jql(query, limit=50)
            issues = []
            for issue in results.get("issues", []):
                fields = issue.get("fields", {})
                assignee = fields.get("assignee") or {}
                issues.append(
                    {
                        "key": issue["key"],
                        "summary": fields.get("summary", ""),
                        "status": (fields.get("status") or {}).get("name", ""),
                        "assignee": assignee.get("displayName", "Unassigned"),
                    }
                )
            return issues
        except ApiError as exc:
            logger.error("JQL search failed for query '%s': %s", query, exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error during JQL search: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def add_comment(self, ticket_key: str, comment: str) -> bool:
        """Add a comment to the specified JIRA ticket.

        Returns ``True`` on success, ``False`` otherwise.
        """
        try:
            self._client.issue_add_comment(ticket_key, comment)
            logger.info("Added comment to %s", ticket_key)
            return True
        except ApiError as exc:
            logger.error("Failed to add comment to %s: %s", ticket_key, exc)
            return False
        except Exception as exc:
            logger.error("Unexpected error adding comment to %s: %s", ticket_key, exc)
            return False

    # ------------------------------------------------------------------
    # Related-ticket discovery
    # ------------------------------------------------------------------

    def find_related_tickets(self, repo_url: str, branch: str) -> list[dict]:
        """Find JIRA tickets related to a repository and branch.

        Searches by:
        1. Branch name appearing in ticket text (common when branches
           follow ``PROJ-123/feature-name`` conventions).
        2. Repository URL mentioned in ticket comments or descriptions.

        Returns the same dict shape as :meth:`search_tickets`.
        """
        # Extract a potential ticket key from the branch name.
        # Convention: branches like "PROJ-123-some-description"
        branch_prefix = branch.split("/")[-1]  # handle "feature/PROJ-123-foo"
        parts = branch_prefix.split("-")

        jql_clauses: list[str] = []

        # If the branch starts with a ticket-key pattern (ABC-123), search by key.
        if len(parts) >= 2 and parts[0].isalpha() and parts[1].isdigit():
            ticket_key_guess = f"{parts[0].upper()}-{parts[1]}"
            jql_clauses.append(f'key = "{ticket_key_guess}"')

        # Also do a text search for the branch name and repo URL.
        jql_clauses.append(f'text ~ "{branch_prefix}"')
        jql_clauses.append(f'text ~ "{repo_url}"')

        jql = " OR ".join(jql_clauses)
        return self.search_tickets(jql)
