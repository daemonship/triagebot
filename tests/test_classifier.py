"""Tests for the classifier — mocks OpenAI to avoid real API calls."""

import json
from unittest.mock import MagicMock, patch

import pytest

from triagebot.classifier import Classifier, ClassificationResult

CATEGORIES = ["bug", "feature-request", "question", "documentation"]


def _mock_response(category: str, confidence: float) -> MagicMock:
    msg = MagicMock()
    msg.content = json.dumps({"category": category, "confidence": confidence})
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_high_confidence_classification():
    with patch("triagebot.classifier.OpenAI") as mock_openai_cls:
        client = mock_openai_cls.return_value
        client.chat.completions.create.return_value = _mock_response("bug", 0.95)
        clf = Classifier("fake-key")
        result = clf.classify("App crashes on startup", "It crashes", CATEGORIES)
        assert result.category == "bug"
        assert result.confidence == pytest.approx(0.95)


def test_low_confidence_returns_provided_category():
    with patch("triagebot.classifier.OpenAI") as mock_openai_cls:
        client = mock_openai_cls.return_value
        client.chat.completions.create.return_value = _mock_response("question", 0.4)
        clf = Classifier("fake-key")
        result = clf.classify("unclear issue", "dunno", CATEGORIES)
        # Classifier returns what the LLM says — it's main.py that decides what label to apply
        assert result.category == "question"
        assert result.confidence == pytest.approx(0.4)


def test_unknown_category_falls_back_to_needs_triage():
    with patch("triagebot.classifier.OpenAI") as mock_openai_cls:
        client = mock_openai_cls.return_value
        client.chat.completions.create.return_value = _mock_response("spam", 0.99)
        clf = Classifier("fake-key")
        result = clf.classify("title", "body", CATEGORIES)
        assert result.category == "needs-triage"
        assert result.confidence == 0.0


def test_api_failure_falls_back_to_needs_triage():
    with patch("triagebot.classifier.OpenAI") as mock_openai_cls:
        client = mock_openai_cls.return_value
        client.chat.completions.create.side_effect = Exception("connection failed")
        clf = Classifier("fake-key")
        result = clf.classify("title", "body", CATEGORIES)
        assert result.category == "needs-triage"
        assert result.confidence == 0.0
