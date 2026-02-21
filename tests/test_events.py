"""Tests for GitHub event parsing."""


from triagebot.events import IssueEvent, parse_event


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
