"""Config loading from .github/triagebot.yml with sensible defaults."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError, field_validator


DEFAULT_CATEGORIES = ["bug", "feature-request", "question", "documentation"]
DEFAULT_REQUIRED_FIELDS = ["reproduction steps", "expected behavior", "actual behavior"]


class ClassificationConfig(BaseModel):
    categories: list[str] = DEFAULT_CATEGORIES

    @field_validator("categories")
    @classmethod
    def categories_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("classification.categories must not be empty")
        return [c.strip().lower() for c in v]


class MissingInfoConfig(BaseModel):
    required_fields: list[str] = DEFAULT_REQUIRED_FIELDS

    @field_validator("required_fields")
    @classmethod
    def fields_not_empty(cls, v: list[str]) -> list[str]:
        return [f.strip().lower() for f in v]


class TriageBotConfig(BaseModel):
    classification: ClassificationConfig = ClassificationConfig()
    missing_info: MissingInfoConfig = MissingInfoConfig()


def load_config(repo_root: Path | None = None) -> TriageBotConfig:
    """Load config from .github/triagebot.yml. Returns defaults if file absent."""
    config_path_env = os.environ.get("TRIAGEBOT_CONFIG_PATH", ".github/triagebot.yml")

    if repo_root is None:
        repo_root = Path(os.environ.get("GITHUB_WORKSPACE", "."))

    config_file = repo_root / config_path_env

    if not config_file.exists():
        return TriageBotConfig()

    raw = yaml.safe_load(config_file.read_text()) or {}
    try:
        return TriageBotConfig.model_validate(raw)
    except ValidationError as e:
        # Fail fast with a clear message so users know their config is broken
        raise SystemExit(f"TriageBot: invalid config at {config_file}:\n{e}") from e
