"""Tests for missing info heuristic detection."""

import pytest

from triagebot.missing_info import find_missing_fields, build_missing_info_comment

DEFAULT_FIELDS = ["reproduction steps", "expected behavior", "actual behavior"]


def test_empty_body_returns_all_fields():
    missing = find_missing_fields("", DEFAULT_FIELDS)
    assert set(missing) == set(DEFAULT_FIELDS)


def test_very_short_body_returns_all_fields():
    missing = find_missing_fields("it broken", DEFAULT_FIELDS)
    assert set(missing) == set(DEFAULT_FIELDS)


def test_body_with_all_headers_passes():
    body = textwrap.dedent("""\
        ## Steps to Reproduce
        1. Open app
        2. Click button

        ## Expected Behavior
        Nothing crashes.

        ## Actual Behavior
        It crashes.
    """)
    missing = find_missing_fields(body, DEFAULT_FIELDS)
    assert missing == []


def test_body_missing_one_field():
    body = textwrap.dedent("""\
        ## Steps to Reproduce
        1. Do thing

        ## Expected Behavior
        Works fine.
    """)
    missing = find_missing_fields(body, DEFAULT_FIELDS)
    assert "actual behavior" in missing
    assert "reproduction steps" not in missing


def test_bold_labels_recognized():
    body = (
        "**Steps to Reproduce:** do the thing\n"
        "**Expected Behavior:** works\n"
        "**Actual Behavior:** crashes\n"
        "This is a longer body with enough text to pass the length check minimum.\n"
    )
    missing = find_missing_fields(body, DEFAULT_FIELDS)
    assert missing == []


def test_missing_info_comment_format():
    comment = build_missing_info_comment(["reproduction steps", "expected behavior"])
    assert "Reproduction Steps" in comment
    assert "Expected Behavior" in comment
    assert "needs-info" in comment
    assert "TriageBot" in comment


import textwrap
