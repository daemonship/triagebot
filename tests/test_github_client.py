"""Tests for the GitHub REST API client."""

import pytest
import httpx
from pytest_httpx import HTTPXMock

from triagebot.github_client import GitHubClient, GITHUB_API

REPO = "testowner/testrepo"
TOKEN = "ghs_test_token"
ISSUE_NUM = 42


@pytest.fixture
def client(httpx_mock: HTTPXMock) -> GitHubClient:
    return GitHubClient(TOKEN, REPO)


def _label_url(label: str | None = None) -> str:
    base = f"{GITHUB_API}/repos/{REPO}/labels"
    return f"{base}/{label}" if label else base


def _issue_labels_url() -> str:
    return f"{GITHUB_API}/repos/{REPO}/issues/{ISSUE_NUM}/labels"


def _comments_url() -> str:
    return f"{GITHUB_API}/repos/{REPO}/issues/{ISSUE_NUM}/comments"


# ---------------------------------------------------------------------------
# get_issue_labels
# ---------------------------------------------------------------------------

def test_get_issue_labels(client: GitHubClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=_issue_labels_url(),
        json=[{"name": "bug"}, {"name": "needs-info"}],
    )
    labels = client.get_issue_labels(ISSUE_NUM)
    assert labels == ["bug", "needs-info"]


def test_get_issue_labels_empty(client: GitHubClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_issue_labels_url(), json=[])
    assert client.get_issue_labels(ISSUE_NUM) == []


def test_get_issue_labels_api_error(client: GitHubClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_issue_labels_url(), status_code=403, text="Forbidden")
    with pytest.raises(RuntimeError, match="403"):
        client.get_issue_labels(ISSUE_NUM)


# ---------------------------------------------------------------------------
# add_label (includes _ensure_label_exists)
# ---------------------------------------------------------------------------

def test_add_label_when_label_exists(client: GitHubClient, httpx_mock: HTTPXMock):
    # Label already exists on the repo
    httpx_mock.add_response(url=_label_url("bug"), status_code=200, json={"name": "bug"})
    httpx_mock.add_response(url=_issue_labels_url(), status_code=200, json=[{"name": "bug"}])
    client.add_label(ISSUE_NUM, "bug")


def test_add_label_creates_missing_label(client: GitHubClient, httpx_mock: HTTPXMock):
    # Label doesn't exist → create it, then apply it
    httpx_mock.add_response(url=_label_url("bug"), status_code=404, json={})
    httpx_mock.add_response(url=_label_url(), status_code=201, json={"name": "bug"})
    httpx_mock.add_response(url=_issue_labels_url(), status_code=200, json=[{"name": "bug"}])
    client.add_label(ISSUE_NUM, "bug")


def test_add_label_race_condition_422_is_ok(client: GitHubClient, httpx_mock: HTTPXMock):
    # Label creation hits a 422 (already exists race) — should not raise
    httpx_mock.add_response(url=_label_url("bug"), status_code=404, json={})
    httpx_mock.add_response(url=_label_url(), status_code=422, json={})
    httpx_mock.add_response(url=_issue_labels_url(), status_code=200, json=[{"name": "bug"}])
    client.add_label(ISSUE_NUM, "bug")


# ---------------------------------------------------------------------------
# remove_label
# ---------------------------------------------------------------------------

def test_remove_label_success(client: GitHubClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{GITHUB_API}/repos/{REPO}/issues/{ISSUE_NUM}/labels/needs-info",
        status_code=200,
        json=[],
    )
    client.remove_label(ISSUE_NUM, "needs-info")  # should not raise


def test_remove_label_not_present_is_silent(client: GitHubClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{GITHUB_API}/repos/{REPO}/issues/{ISSUE_NUM}/labels/needs-info",
        status_code=404,
        json={},
    )
    client.remove_label(ISSUE_NUM, "needs-info")  # 404 → silently ignored


def test_remove_label_api_error(client: GitHubClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{GITHUB_API}/repos/{REPO}/issues/{ISSUE_NUM}/labels/needs-info",
        status_code=500,
        text="Server error",
    )
    with pytest.raises(RuntimeError, match="500"):
        client.remove_label(ISSUE_NUM, "needs-info")


# ---------------------------------------------------------------------------
# post_comment
# ---------------------------------------------------------------------------

def test_post_comment(client: GitHubClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_comments_url(), status_code=201, json={"id": 1})
    client.post_comment(ISSUE_NUM, "Please add reproduction steps.")


def test_post_comment_api_error(client: GitHubClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_comments_url(), status_code=403, text="Forbidden")
    with pytest.raises(RuntimeError, match="403"):
        client.post_comment(ISSUE_NUM, "comment")


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

def test_context_manager(httpx_mock: HTTPXMock):
    with GitHubClient(TOKEN, REPO) as gh:
        httpx_mock.add_response(url=_issue_labels_url(), json=[])
        labels = gh.get_issue_labels(ISSUE_NUM)
    assert labels == []


# ---------------------------------------------------------------------------
# Auth header
# ---------------------------------------------------------------------------

def test_auth_header_sent(client: GitHubClient, httpx_mock: HTTPXMock):
    def check_auth(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        return httpx.Response(200, json=[])

    httpx_mock.add_callback(check_auth, url=_issue_labels_url())
    client.get_issue_labels(ISSUE_NUM)
