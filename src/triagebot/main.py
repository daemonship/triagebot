"""TriageBot entry point — reads GitHub event and dispatches to handlers."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional

from .classifier import Classifier
from .config import load_config
from .events import CommentEvent, IssueEvent, parse_comment_event, parse_event
from .github_client import GitHubClient
from .missing_info import build_missing_info_comment, find_missing_fields

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [triagebot] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

NEEDS_TRIAGE_LABEL = "needs-triage"
NEEDS_INFO_LABEL = "needs-info"
CONFIDENCE_THRESHOLD = 0.7

_SLASH_LABEL_RE = re.compile(r"^/label\s+(\S+)\s*$", re.MULTILINE | re.IGNORECASE)
_SLASH_RECLASSIFY_RE = re.compile(r"^/reclassify\s*$", re.MULTILINE | re.IGNORECASE)

_LOW_CONFIDENCE_COMMENT = """\
👋 Thanks for opening this issue!

TriageBot wasn't confident enough to automatically assign a category \
(confidence: {confidence:.0%}). A maintainer will review and label it shortly.

If you'd like to help speed things up, feel free to clarify the issue type in a comment.
"""


def _load_event() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("GITHUB_EVENT_PATH not set — is this running inside a GitHub Action?")
    return json.loads(Path(event_path).read_text())


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Required environment variable {name} is not set.")
    return value


def handle_opened(
    event: IssueEvent,
    gh: GitHubClient,
    classifier: Optional[Classifier],
    categories: list[str],
    required_fields: list[str],
) -> None:
    logger.info("Processing opened issue #%d: %s", event.number, event.title[:80])

    # --- Classification ---
    if classifier is None:
        logger.info("Classification disabled — skipping LLM call")
    else:
        result = classifier.classify(event.title, event.body, categories)
        logger.info(
            "Classification: category=%r confidence=%.2f", result.category, result.confidence
        )

        if result.confidence >= CONFIDENCE_THRESHOLD:
            gh.add_label(event.number, result.category)
            logger.info("Applied label %r", result.category)
        else:
            gh.add_label(event.number, NEEDS_TRIAGE_LABEL)
            gh.post_comment(
                event.number,
                _LOW_CONFIDENCE_COMMENT.format(confidence=result.confidence),
            )
            logger.info(
                "Low confidence (%.2f < %.2f), applied %r and posted comment",
                result.confidence,
                CONFIDENCE_THRESHOLD,
                NEEDS_TRIAGE_LABEL,
            )

    # --- Missing info check ---
    missing = find_missing_fields(event.body, required_fields)
    if missing:
        logger.info("Missing fields: %s", missing)
        gh.add_label(event.number, NEEDS_INFO_LABEL)
        gh.post_comment(event.number, build_missing_info_comment(missing))
    else:
        logger.info("All required fields present")


def handle_edited(
    event: IssueEvent,
    gh: GitHubClient,
    required_fields: list[str],
) -> None:
    """On edit, re-check missing info only. Do not re-classify."""
    # Use labels from the event payload — avoids an extra API call.
    if NEEDS_INFO_LABEL not in event.labels:
        logger.info("Issue #%d edited but no needs-info label — nothing to do", event.number)
        return

    missing = find_missing_fields(event.body, required_fields)
    if not missing:
        gh.remove_label(event.number, NEEDS_INFO_LABEL)
        logger.info(
            "Issue #%d now has all required fields — removed %r",
            event.number,
            NEEDS_INFO_LABEL,
        )
    else:
        logger.info("Issue #%d edited but still missing: %s", event.number, missing)


def handle_comment(
    event: CommentEvent,
    gh: GitHubClient,
    classifier: Optional[Classifier],
    categories: list[str],
) -> None:
    """Handle slash commands posted in issue comments.

    Recognized commands:
      /label <category>  — override the classification label
      /reclassify        — re-run LLM classification on the issue
    """
    body = event.comment_body

    label_match = _SLASH_LABEL_RE.search(body)
    reclassify_match = _SLASH_RECLASSIFY_RE.search(body)

    if label_match:
        requested = label_match.group(1).lower()
        if requested not in categories:
            logger.info(
                "Unknown category %r in /label command — valid: %s", requested, categories
            )
            return
        # Remove existing category labels and needs-triage before applying override
        for lbl in event.issue_labels:
            if lbl in categories or lbl == NEEDS_TRIAGE_LABEL:
                gh.remove_label(event.issue_number, lbl)
        gh.add_label(event.issue_number, requested)
        logger.info("Applied /label %r to issue #%d", requested, event.issue_number)

    elif reclassify_match:
        if classifier is None:
            logger.info("Classification disabled — /reclassify ignored on issue #%d", event.issue_number)
            return
        result = classifier.classify(event.issue_title, event.issue_body, categories)
        logger.info(
            "/reclassify issue #%d: category=%r confidence=%.2f",
            event.issue_number,
            result.category,
            result.confidence,
        )
        if result.confidence >= CONFIDENCE_THRESHOLD:
            for lbl in event.issue_labels:
                if lbl in categories or lbl == NEEDS_TRIAGE_LABEL:
                    gh.remove_label(event.issue_number, lbl)
            gh.add_label(event.issue_number, result.category)
        else:
            gh.add_label(event.issue_number, NEEDS_TRIAGE_LABEL)
            gh.post_comment(
                event.issue_number,
                _LOW_CONFIDENCE_COMMENT.format(confidence=result.confidence),
            )

    else:
        logger.info(
            "Comment on issue #%d has no recognized slash command — nothing to do",
            event.issue_number,
        )


def main() -> None:
    github_token = _require_env("GITHUB_TOKEN")
    repo = _require_env("GITHUB_REPOSITORY")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    raw_event = _load_event()
    config = load_config()
    categories = config.classification.categories
    required_fields = config.missing_info.required_fields

    logger.info(
        "Config: categories=%s required_fields=%s classification_enabled=%s",
        categories,
        required_fields,
        config.classification.enabled,
    )

    with GitHubClient(github_token, repo) as gh:
        if event_name == "issues":
            issue_event = parse_event(raw_event)
            if not issue_event:
                logger.warning("Event has no 'issue' payload — skipping")
                sys.exit(0)

            if config.classification.enabled:
                openai_api_key = _require_env("OPENAI_API_KEY")
                openai_base_url = os.environ.get("OPENAI_BASE_URL") or None
                openai_model = os.environ.get("OPENAI_MODEL") or None
                classifier: Optional[Classifier] = Classifier(
                    openai_api_key, base_url=openai_base_url, model=openai_model
                )
            else:
                logger.info("Classification disabled via config — no LLM calls will be made")
                classifier = None

            if issue_event.action == "opened":
                handle_opened(issue_event, gh, classifier, categories, required_fields)
            elif issue_event.action == "edited":
                handle_edited(issue_event, gh, required_fields)
            else:
                logger.info("Action %r — nothing to do", issue_event.action)

        elif event_name == "issue_comment":
            comment_event = parse_comment_event(raw_event)
            if not comment_event:
                logger.warning("Event has no comment payload — skipping")
                sys.exit(0)

            if comment_event.action != "created":
                logger.info("Comment action %r — nothing to do", comment_event.action)
                sys.exit(0)

            # Build classifier only if enabled and API key is available
            classifier = None
            if config.classification.enabled:
                openai_api_key = os.environ.get("OPENAI_API_KEY")
                if openai_api_key:
                    openai_base_url = os.environ.get("OPENAI_BASE_URL") or None
                    openai_model = os.environ.get("OPENAI_MODEL") or None
                    classifier = Classifier(
                        openai_api_key, base_url=openai_base_url, model=openai_model
                    )
                else:
                    logger.info("OPENAI_API_KEY not set — /reclassify will be unavailable")

            handle_comment(comment_event, gh, classifier, categories)

        else:
            logger.info("Event %r is not handled — nothing to do", event_name)
            sys.exit(0)


if __name__ == "__main__":
    main()
