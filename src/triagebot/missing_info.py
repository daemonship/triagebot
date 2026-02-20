"""Heuristic detection of missing required fields in issue bodies."""

from __future__ import annotations

import re

# Minimum body length before we consider it substantive enough to skip field checks.
_MIN_BODY_LENGTH = 50


def find_missing_fields(body: str, required_fields: list[str]) -> list[str]:
    """Return list of required fields not found in the issue body.

    Uses lightweight heuristics — no LLM call:
    - Checks for section headers matching the field name (e.g. "## Steps to reproduce")
    - Checks for keyword presence in the body text
    - Skips check entirely if body is too short (whole thing is probably missing)
    """
    if not body or len(body.strip()) < _MIN_BODY_LENGTH:
        # Body is nearly empty — report all fields as missing
        return list(required_fields)

    body_lower = body.lower()
    missing = []

    for field in required_fields:
        if not _field_present(field, body_lower):
            missing.append(field)

    return missing


def _field_present(field: str, body_lower: str) -> bool:
    """Check whether a required field appears to be addressed in the issue body.

    Checks for the field (or a known alias) appearing in a markdown header or bold label.
    Only structured markup is checked — raw prose is not counted to avoid false positives.
    """
    phrases = _field_phrases(field)

    for phrase in phrases:
        # Markdown header: ## Phrase or ## Something Phrase Something
        header_pattern = re.compile(
            r"^#{1,4}\s+[^\n]*" + re.escape(phrase),
            re.MULTILINE,
        )
        if header_pattern.search(body_lower):
            return True

        # Bold label: **Phrase** or **Phrase:**
        bold_pattern = re.compile(r"\*\*[^*]*" + re.escape(phrase) + r"[^*]*\*\*")
        if bold_pattern.search(body_lower):
            return True

    return False


def _field_phrases(field: str) -> list[str]:
    """Return the field and its known aliases as matchable phrases."""
    field_lower = field.lower()

    aliases: dict[str, list[str]] = {
        "reproduction steps": ["reproduction steps", "steps to reproduce", "how to reproduce", "repro steps"],
        "expected behavior": ["expected behavior", "expected behaviour", "expected result"],
        "actual behavior": ["actual behavior", "actual behaviour", "actual result", "current behavior"],
        "environment": ["environment", "system info", "platform"],
        "stack trace": ["stack trace", "traceback", "error output"],
        "version": ["version"],
    }

    return aliases.get(field_lower, [field_lower])


def build_missing_info_comment(missing_fields: list[str]) -> str:
    """Build the comment text posted when required fields are absent."""
    field_list = "\n".join(f"- **{f.title()}**" for f in missing_fields)
    return (
        "Thanks for opening this issue! To help us resolve it quickly, "
        "could you please add the following information?\n\n"
        f"{field_list}\n\n"
        "_This message was posted automatically by TriageBot. "
        "Once you've added the missing details, the `needs-info` label will be removed._"
    )
