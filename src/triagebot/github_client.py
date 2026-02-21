"""Thin GitHub REST API client using httpx."""

from __future__ import annotations

import logging

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str, repo: str) -> None:
        """
        Args:
            token: GitHub token with issues:write permission.
            repo: Full repo name, e.g. "owner/myrepo".
        """
        self._repo = repo
        self._client = httpx.Client(
            base_url=GITHUB_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )

    def _raise(self, resp: httpx.Response) -> None:
        if not resp.is_success:
            logger.warning(
                "GitHub API %s %s → %s",
                resp.request.method,
                resp.request.url,
                resp.status_code,
            )
            raise RuntimeError(
                f"GitHub API {resp.request.method} {resp.request.url} "
                f"→ {resp.status_code}: {resp.text[:200]}"
            )

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute an HTTP request, retrying on transient network failures."""
        return self._client.request(method, url, **kwargs)

    def get_issue_labels(self, issue_number: int) -> list[str]:
        resp = self._request("GET", f"/repos/{self._repo}/issues/{issue_number}/labels")
        self._raise(resp)
        return [label["name"] for label in resp.json()]

    def add_label(self, issue_number: int, label: str) -> None:
        """Add a label to an issue. Creates the label on the repo if it doesn't exist."""
        self._ensure_label_exists(label)
        resp = self._request(
            "POST",
            f"/repos/{self._repo}/issues/{issue_number}/labels",
            json={"labels": [label]},
        )
        self._raise(resp)

    def remove_label(self, issue_number: int, label: str) -> None:
        """Remove a label from an issue. Silently ignores if label not present."""
        resp = self._request(
            "DELETE",
            f"/repos/{self._repo}/issues/{issue_number}/labels/{label}",
        )
        if resp.status_code == 404:
            return  # Label wasn't on the issue — nothing to do
        self._raise(resp)

    def post_comment(self, issue_number: int, body: str) -> None:
        resp = self._request(
            "POST",
            f"/repos/{self._repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        self._raise(resp)

    def _ensure_label_exists(self, label: str) -> None:
        """Create the label on the repo if it doesn't already exist."""
        # Check existence
        resp = self._request("GET", f"/repos/{self._repo}/labels/{label}")
        if resp.status_code == 200:
            return
        if resp.status_code != 404:
            self._raise(resp)

        # Create it with a neutral color
        color_map = {
            "bug": "d73a4a",
            "feature-request": "a2eeef",
            "question": "d876e3",
            "documentation": "0075ca",
            "needs-triage": "e4e669",
            "needs-info": "f9d0c4",
        }
        color = color_map.get(label, "ededed")
        resp = self._request(
            "POST",
            f"/repos/{self._repo}/labels",
            json={"name": label, "color": color},
        )
        # 422 = already exists (race condition) — ignore
        if resp.status_code not in (201, 422):
            self._raise(resp)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
