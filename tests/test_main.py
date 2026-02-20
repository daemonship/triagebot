"""Tests for handle_opened and handle_edited dispatch logic."""

from unittest.mock import MagicMock, call

import pytest

from triagebot.classifier import ClassificationResult
from triagebot.events import IssueEvent
from triagebot.main import CONFIDENCE_THRESHOLD, NEEDS_INFO_LABEL, NEEDS_TRIAGE_LABEL, handle_edited, handle_opened

CATEGORIES = ["bug", "feature-request", "question", "documentation"]
REQUIRED_FIELDS = ["reproduction steps", "expected behavior", "actual behavior"]

_FULL_BODY = (
    "## Steps to Reproduce\n1. Do the thing\n\n"
    "## Expected Behavior\nWorks fine.\n\n"
    "## Actual Behavior\nCrashes badly.\n"
)


def _make_event(action="opened", labels=None, body=_FULL_BODY):
    return IssueEvent(
        action=action,
        number=42,
        title="App crashes",
        body=body,
        labels=labels or [],
    )


def _make_gh():
    return MagicMock()


def _make_classifier(category="bug", confidence=0.95):
    clf = MagicMock()
    clf.classify.return_value = ClassificationResult(category=category, confidence=confidence)
    return clf


# ---------------------------------------------------------------------------
# handle_opened — high-confidence path
# ---------------------------------------------------------------------------


def test_high_confidence_applies_category_label():
    gh = _make_gh()
    clf = _make_classifier("bug", 0.95)
    handle_opened(_make_event(), gh, clf, CATEGORIES, REQUIRED_FIELDS)

    gh.add_label.assert_any_call(42, "bug")
    gh.post_comment.assert_not_called()


def test_high_confidence_no_needs_triage():
    gh = _make_gh()
    clf = _make_classifier("feature-request", 0.80)
    handle_opened(_make_event(), gh, clf, CATEGORIES, REQUIRED_FIELDS)

    applied_labels = [c.args[1] for c in gh.add_label.call_args_list]
    assert NEEDS_TRIAGE_LABEL not in applied_labels


# ---------------------------------------------------------------------------
# handle_opened — low-confidence path
# ---------------------------------------------------------------------------


def test_low_confidence_applies_needs_triage_label():
    gh = _make_gh()
    clf = _make_classifier("bug", CONFIDENCE_THRESHOLD - 0.01)
    handle_opened(_make_event(), gh, clf, CATEGORIES, REQUIRED_FIELDS)

    applied_labels = [c.args[1] for c in gh.add_label.call_args_list]
    assert NEEDS_TRIAGE_LABEL in applied_labels


def test_low_confidence_posts_comment():
    gh = _make_gh()
    clf = _make_classifier("bug", 0.50)
    handle_opened(_make_event(), gh, clf, CATEGORIES, REQUIRED_FIELDS)

    gh.post_comment.assert_called_once()
    comment_body = gh.post_comment.call_args.args[1]
    assert "50%" in comment_body  # confidence formatted as percentage


def test_low_confidence_does_not_apply_category_label():
    gh = _make_gh()
    clf = _make_classifier("bug", 0.30)
    handle_opened(_make_event(), gh, clf, CATEGORIES, REQUIRED_FIELDS)

    applied_labels = [c.args[1] for c in gh.add_label.call_args_list]
    assert "bug" not in applied_labels


# ---------------------------------------------------------------------------
# handle_opened — missing info path
# ---------------------------------------------------------------------------


def test_missing_info_adds_needs_info_label():
    gh = _make_gh()
    clf = _make_classifier("bug", 0.95)
    handle_opened(_make_event(body="short body"), gh, clf, CATEGORIES, REQUIRED_FIELDS)

    applied_labels = [c.args[1] for c in gh.add_label.call_args_list]
    assert NEEDS_INFO_LABEL in applied_labels
    gh.post_comment.assert_called_once()


def test_missing_info_comment_names_missing_fields():
    """The posted comment must list each missing field so the reporter knows what to add."""
    gh = _make_gh()
    clf = _make_classifier("bug", 0.95)
    handle_opened(_make_event(body="short body"), gh, clf, CATEGORIES, REQUIRED_FIELDS)

    comment_body = gh.post_comment.call_args.args[1]
    assert "Reproduction Steps" in comment_body
    assert "Expected Behavior" in comment_body
    assert "Actual Behavior" in comment_body


def test_complete_body_no_needs_info():
    gh = _make_gh()
    clf = _make_classifier("bug", 0.95)
    handle_opened(_make_event(body=_FULL_BODY), gh, clf, CATEGORIES, REQUIRED_FIELDS)

    applied_labels = [c.args[1] for c in gh.add_label.call_args_list]
    assert NEEDS_INFO_LABEL not in applied_labels


def test_edited_no_reclassification():
    """handle_edited must never call the classifier — only re-check missing fields."""
    clf = _make_classifier()
    gh = _make_gh()
    event = _make_event(action="edited", labels=[NEEDS_INFO_LABEL], body=_FULL_BODY)
    handle_edited(event, gh, REQUIRED_FIELDS)

    clf.classify.assert_not_called()


# ---------------------------------------------------------------------------
# handle_edited
# ---------------------------------------------------------------------------


def test_edited_with_needs_info_and_still_missing_keeps_label():
    gh = _make_gh()
    event = _make_event(action="edited", labels=[NEEDS_INFO_LABEL], body="too short")
    handle_edited(event, gh, REQUIRED_FIELDS)

    gh.remove_label.assert_not_called()


def test_edited_with_needs_info_and_now_complete_removes_label():
    gh = _make_gh()
    event = _make_event(action="edited", labels=[NEEDS_INFO_LABEL], body=_FULL_BODY)
    handle_edited(event, gh, REQUIRED_FIELDS)

    gh.remove_label.assert_called_once_with(42, NEEDS_INFO_LABEL)


def test_edited_without_needs_info_label_does_nothing():
    gh = _make_gh()
    event = _make_event(action="edited", labels=[], body="too short")
    handle_edited(event, gh, REQUIRED_FIELDS)

    gh.remove_label.assert_not_called()
    gh.add_label.assert_not_called()
    gh.post_comment.assert_not_called()
