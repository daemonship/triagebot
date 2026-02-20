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
