"""Tests for handle_opened, handle_edited, and handle_comment dispatch logic."""

from unittest.mock import MagicMock


from triagebot.classifier import ClassificationResult
from triagebot.events import CommentEvent, IssueEvent
from triagebot.main import CONFIDENCE_THRESHOLD, NEEDS_INFO_LABEL, NEEDS_TRIAGE_LABEL, handle_comment, handle_edited, handle_opened

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


# ---------------------------------------------------------------------------
# handle_opened — classification disabled (classifier=None)
# ---------------------------------------------------------------------------


def test_classification_disabled_skips_llm():
    """When classifier is None, no classification label should be applied."""
    gh = _make_gh()
    handle_opened(_make_event(body=_FULL_BODY), gh, None, CATEGORIES, REQUIRED_FIELDS)

    applied_labels = [c.args[1] for c in gh.add_label.call_args_list]
    assert "bug" not in applied_labels
    assert NEEDS_TRIAGE_LABEL not in applied_labels


def test_classification_disabled_still_checks_missing_info():
    """Missing-info detection must still run even when classification is disabled."""
    gh = _make_gh()
    handle_opened(_make_event(body="short body"), gh, None, CATEGORIES, REQUIRED_FIELDS)

    applied_labels = [c.args[1] for c in gh.add_label.call_args_list]
    assert NEEDS_INFO_LABEL in applied_labels
    gh.post_comment.assert_called_once()


def test_classification_disabled_no_api_comment():
    """No low-confidence comment should be posted when classification is disabled."""
    gh = _make_gh()
    handle_opened(_make_event(body=_FULL_BODY), gh, None, CATEGORIES, REQUIRED_FIELDS)

    gh.post_comment.assert_not_called()


# ---------------------------------------------------------------------------
# handle_comment — /label command
# ---------------------------------------------------------------------------


def _make_comment_event(comment_body="/label bug", issue_labels=None):
    return CommentEvent(
        action="created",
        issue_number=42,
        issue_title="App crashes",
        issue_body=_FULL_BODY,
        issue_labels=issue_labels or [],
        comment_body=comment_body,
    )


def test_slash_label_applies_requested_label():
    gh = _make_gh()
    handle_comment(_make_comment_event("/label feature-request"), gh, None, CATEGORIES)
    gh.add_label.assert_called_once_with(42, "feature-request")


def test_slash_label_removes_existing_category_labels():
    gh = _make_gh()
    event = _make_comment_event("/label bug", issue_labels=["feature-request", "needs-triage"])
    handle_comment(event, gh, None, CATEGORIES)

    removed = [c.args[1] for c in gh.remove_label.call_args_list]
    assert "feature-request" in removed
    assert "needs-triage" in removed
    gh.add_label.assert_called_once_with(42, "bug")


def test_slash_label_unknown_category_does_nothing():
    gh = _make_gh()
    handle_comment(_make_comment_event("/label unknown-thing"), gh, None, CATEGORIES)
    gh.add_label.assert_not_called()
    gh.remove_label.assert_not_called()


def test_slash_label_case_insensitive():
    gh = _make_gh()
    handle_comment(_make_comment_event("/Label Bug"), gh, None, CATEGORIES)
    gh.add_label.assert_called_once_with(42, "bug")


def test_slash_label_in_multiline_comment():
    gh = _make_gh()
    body = "Thanks for the triage!\n\n/label question\n\nMore text here."
    handle_comment(_make_comment_event(body), gh, None, CATEGORIES)
    gh.add_label.assert_called_once_with(42, "question")


# ---------------------------------------------------------------------------
# handle_comment — /reclassify command
# ---------------------------------------------------------------------------


def test_slash_reclassify_applies_high_confidence_label():
    gh = _make_gh()
    clf = _make_classifier("bug", 0.90)
    event = _make_comment_event("/reclassify", issue_labels=["needs-triage"])
    handle_comment(event, gh, clf, CATEGORIES)

    removed = [c.args[1] for c in gh.remove_label.call_args_list]
    assert "needs-triage" in removed
    gh.add_label.assert_called_once_with(42, "bug")


def test_slash_reclassify_low_confidence_applies_needs_triage():
    gh = _make_gh()
    clf = _make_classifier("bug", CONFIDENCE_THRESHOLD - 0.01)
    handle_comment(_make_comment_event("/reclassify"), gh, clf, CATEGORIES)

    applied = [c.args[1] for c in gh.add_label.call_args_list]
    assert NEEDS_TRIAGE_LABEL in applied
    gh.post_comment.assert_called_once()


def test_slash_reclassify_disabled_classifier_does_nothing():
    gh = _make_gh()
    handle_comment(_make_comment_event("/reclassify"), gh, None, CATEGORIES)
    gh.add_label.assert_not_called()
    gh.remove_label.assert_not_called()


# ---------------------------------------------------------------------------
# handle_comment — no slash command
# ---------------------------------------------------------------------------


def test_non_slash_comment_does_nothing():
    gh = _make_gh()
    handle_comment(_make_comment_event("Just a regular comment, no commands."), gh, None, CATEGORIES)
    gh.add_label.assert_not_called()
    gh.remove_label.assert_not_called()
    gh.post_comment.assert_not_called()
