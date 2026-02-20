"""Tests for config loading."""

import textwrap
from pathlib import Path

import pytest

from triagebot.config import (
    DEFAULT_CATEGORIES,
    DEFAULT_REQUIRED_FIELDS,
    TriageBotConfig,
    load_config,
)


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("TRIAGEBOT_CONFIG_PATH", ".github/triagebot.yml")
    config = load_config(tmp_path)
    assert config.classification.categories == DEFAULT_CATEGORIES
    assert config.missing_info.required_fields == DEFAULT_REQUIRED_FIELDS


def test_custom_categories(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIAGEBOT_CONFIG_PATH", ".github/triagebot.yml")
    cfg_dir = tmp_path / ".github"
    cfg_dir.mkdir()
    (cfg_dir / "triagebot.yml").write_text(textwrap.dedent("""\
        classification:
          categories:
            - bug
            - enhancement
            - wontfix
    """))
    config = load_config(tmp_path)
    assert config.classification.categories == ["bug", "enhancement", "wontfix"]


def test_custom_required_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIAGEBOT_CONFIG_PATH", ".github/triagebot.yml")
    cfg_dir = tmp_path / ".github"
    cfg_dir.mkdir()
    (cfg_dir / "triagebot.yml").write_text(textwrap.dedent("""\
        missing_info:
          required_fields:
            - version
            - stack trace
    """))
    config = load_config(tmp_path)
    assert config.missing_info.required_fields == ["version", "stack trace"]


def test_invalid_config_exits(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIAGEBOT_CONFIG_PATH", ".github/triagebot.yml")
    cfg_dir = tmp_path / ".github"
    cfg_dir.mkdir()
    (cfg_dir / "triagebot.yml").write_text("classification:\n  categories: []\n")
    with pytest.raises(SystemExit, match="invalid config"):
        load_config(tmp_path)


def test_empty_config_file_uses_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIAGEBOT_CONFIG_PATH", ".github/triagebot.yml")
    cfg_dir = tmp_path / ".github"
    cfg_dir.mkdir()
    (cfg_dir / "triagebot.yml").write_text("")
    config = load_config(tmp_path)
    assert config.classification.categories == DEFAULT_CATEGORIES
