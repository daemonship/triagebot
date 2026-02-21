"""GitHub Actions event parsing — converts raw webhook JSON into typed data objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

EventType = Literal["opened", "edited", "other"]


@dataclass
class IssueEvent:
    """Clean representation of a GitHub issues webhook event payload.

    Attributes:
        action:  The event action — "opened", "edited", or "other".
        number:  The issue number within the repository.
        title:   The issue title (empty string if absent).
        body:    The issue body text (empty string if None).
        labels:  Label names currently applied to the issue.
    """

    action: EventType
    number: int
    title: str
    body: str
    labels: list[str] = field(default_factory=list)


@dataclass
class CommentEvent:
    """Clean representation of a GitHub issue_comment webhook event payload.

    Attributes:
        action:        The event action — typically "created".
        issue_number:  The issue number the comment belongs to.
        issue_title:   The issue title (empty string if absent).
        issue_body:    The issue body text (empty string if None).
        issue_labels:  Label names currently applied to the issue.
        comment_body:  The text of the new comment.
    """

    action: str
    issue_number: int
    issue_title: str
    issue_body: str
    issue_labels: list[str]
    comment_body: str


def parse_event(event: dict) -> IssueEvent | None:
    """Parse a raw GitHub issues webhook event payload into an IssueEvent.

    Args:
        event: The top-level event payload dict (from GITHUB_EVENT_PATH).

    Returns:
        An IssueEvent, or None if the payload has no 'issue' field.
    """
    issue = event.get("issue")
    if not issue:
        return None

    raw_action = event.get("action", "")
    action: EventType = raw_action if raw_action in ("opened", "edited") else "other"

    return IssueEvent(
        action=action,
        number=issue["number"],
        title=issue.get("title") or "",
        body=issue.get("body") or "",
        labels=[lbl["name"] for lbl in issue.get("labels", [])],
    )


def parse_comment_event(event: dict) -> CommentEvent | None:
    """Parse a raw GitHub issue_comment webhook event payload into a CommentEvent.

    Args:
        event: The top-level event payload dict (from GITHUB_EVENT_PATH).

    Returns:
        A CommentEvent, or None if the payload lacks 'issue' or 'comment' fields.
    """
    issue = event.get("issue")
    comment = event.get("comment")
    if not issue or not comment:
        return None

    return CommentEvent(
        action=event.get("action", ""),
        issue_number=issue["number"],
        issue_title=issue.get("title") or "",
        issue_body=issue.get("body") or "",
        issue_labels=[lbl["name"] for lbl in issue.get("labels", [])],
        comment_body=comment.get("body") or "",
    )
