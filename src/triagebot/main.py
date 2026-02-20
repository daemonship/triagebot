"""TriageBot entry point — reads GitHub event and dispatches to handlers."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from .classifier import Classifier
from .config import load_config
from .events import IssueEvent, parse_event
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
    classifier: Classifier,
    categories: list[str],
    required_fields: list[str],
) -> None:
    logger.info("Processing opened issue #%d: %s", event.number, event.title[:80])

    # --- Classification ---
    result = classifier.classify(event.title, event.body, categories)
    logger.info(
        "Classification: category=%r confidence=%.2f", result.category, result.confidence
    )

    if result.confidence >= CONFIDENCE_THRESHOLD:
        gh.add_label(event.number, result.category)
        logger.info("Applied label %r", result.category)
    else:
        gh.add_label(event.number, NEEDS_TRIAGE_LABEL)
        logger.info(
            "Low confidence (%.2f < %.2f), applied %r",
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


def main() -> None:
    github_token = _require_env("GITHUB_TOKEN")
    openai_api_key = _require_env("OPENAI_API_KEY")
    repo = _require_env("GITHUB_REPOSITORY")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    if event_name != "issues":
        logger.info("Event %r is not 'issues' — nothing to do", event_name)
        sys.exit(0)

    raw_event = _load_event()
    issue_event = parse_event(raw_event)

    if not issue_event:
        logger.warning("Event has no 'issue' payload — skipping")
        sys.exit(0)

    config = load_config()
    categories = config.classification.categories
    required_fields = config.missing_info.required_fields

    logger.info(
        "Config: categories=%s required_fields=%s", categories, required_fields
    )

    with GitHubClient(github_token, repo) as gh:
        classifier = Classifier(openai_api_key)

        if issue_event.action == "opened":
            handle_opened(issue_event, gh, classifier, categories, required_fields)
        elif issue_event.action == "edited":
            handle_edited(issue_event, gh, required_fields)
        else:
            logger.info("Action %r — nothing to do", issue_event.action)


if __name__ == "__main__":
    main()
