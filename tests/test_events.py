"""Tests for GitHub event parsing."""


from triagebot.events import IssueEvent, parse_comment_event, parse_event


def _make_event(action: str, number: int = 42, title: str = "Test issue",
                body: str | None = "Issue body", labels: list[str] | None = None) -> dict:
    return {
        "action": action,
        "issue": {
            "number": number,
            "title": title,
            "body": body,
            "labels": [{"name": n} for n in (labels or [])],
        },
    }


def test_parse_opened_event():
    event = _make_event("opened", number=7, title="App crashes", body="It crashes badly")
    result = parse_event(event)
    assert result is not None
    assert result.action == "opened"
    assert result.number == 7
    assert result.title == "App crashes"
    assert result.body == "It crashes badly"
    assert result.labels == []


def test_parse_edited_event_with_labels():
    event = _make_event("edited", number=12, labels=["bug", "needs-info"])
    result = parse_event(event)
    assert result is not None
    assert result.action == "edited"
    assert result.number == 12
    assert "bug" in result.labels
    assert "needs-info" in result.labels


def test_unknown_action_maps_to_other():
    event = _make_event("labeled")
    result = parse_event(event)
    assert result is not None
    assert result.action == "other"


def test_missing_action_maps_to_other():
    event = {
        "issue": {"number": 1, "title": "hi", "body": "body", "labels": []},
    }
    result = parse_event(event)
    assert result is not None
    assert result.action == "other"


def test_none_body_becomes_empty_string():
    event = _make_event("opened", body=None)
    result = parse_event(event)
    assert result is not None
    assert result.body == ""


def test_none_title_becomes_empty_string():
    event = _make_event("opened", title=None)
    result = parse_event(event)
    assert result is not None
    assert result.title == ""


def test_no_issue_returns_none():
    result = parse_event({"action": "opened"})
    assert result is None


def test_empty_event_returns_none():
    result = parse_event({})
    assert result is None


def test_labels_extracted_from_issue_payload():
    event = _make_event("edited", labels=["documentation", "question", "needs-triage"])
    result = parse_event(event)
    assert result is not None
    assert result.labels == ["documentation", "question", "needs-triage"]


def test_issue_event_dataclass_fields():
    ev = IssueEvent(action="opened", number=99, title="t", body="b", labels=["bug"])
    assert ev.action == "opened"
    assert ev.number == 99
    assert ev.title == "t"
    assert ev.body == "b"
    assert ev.labels == ["bug"]


def test_issue_event_default_labels():
    ev = IssueEvent(action="opened", number=1, title="t", body="b")
    assert ev.labels == []


# ---------------------------------------------------------------------------
# parse_comment_event
# ---------------------------------------------------------------------------


def _make_comment_event(
    action: str = "created",
    issue_number: int = 42,
    issue_title: str = "App crashes",
    issue_body: str = "It crashes",
    issue_labels: list[str] | None = None,
    comment_body: str = "/label bug",
) -> dict:
    return {
        "action": action,
        "issue": {
            "number": issue_number,
            "title": issue_title,
            "body": issue_body,
            "labels": [{"name": n} for n in (issue_labels or [])],
        },
        "comment": {
            "body": comment_body,
        },
    }


def test_parse_comment_event_basic():
    raw = _make_comment_event()
    result = parse_comment_event(raw)
    assert result is not None
    assert result.action == "created"
    assert result.issue_number == 42
    assert result.issue_title == "App crashes"
    assert result.issue_body == "It crashes"
    assert result.issue_labels == []
    assert result.comment_body == "/label bug"


def test_parse_comment_event_with_labels():
    raw = _make_comment_event(issue_labels=["bug", "needs-triage"])
    result = parse_comment_event(raw)
    assert result is not None
    assert result.issue_labels == ["bug", "needs-triage"]


def test_parse_comment_event_missing_issue_returns_none():
    result = parse_comment_event({"action": "created", "comment": {"body": "/label bug"}})
    assert result is None


def test_parse_comment_event_missing_comment_returns_none():
    result = parse_comment_event({"action": "created", "issue": {"number": 1, "labels": []}})
    assert result is None


def test_parse_comment_event_none_body_becomes_empty_string():
    raw = _make_comment_event(comment_body=None)
    result = parse_comment_event(raw)
    assert result is not None
    assert result.comment_body == ""


def test_parse_comment_event_non_created_action():
    raw = _make_comment_event(action="deleted")
    result = parse_comment_event(raw)
    assert result is not None
    assert result.action == "deleted"
