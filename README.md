# TriageBot

**TriageBot** is a zero-infrastructure GitHub Action that automatically classifies new issues into categories (`bug`, `feature-request`, `question`, `documentation`) using `gpt-4o-mini`, applies the matching label, checks whether required fields (reproduction steps, expected behavior, actual behavior) are present, and posts a single consolidated comment requesting anything missing — then removes the `needs-info` label automatically once the issue is updated.

## Feedback & Ideas

> **This project is being built in public and we want to hear from you.**
> Found a bug? Have a feature idea? Something feel wrong or missing?
> **[Open an issue](../../issues)** — every piece of feedback directly shapes what gets built next.

## Status

> 🚧 In active development — not yet production ready

| Feature | Status | Notes |
|---------|--------|-------|
| Project scaffold & CI | ✅ Complete | pyproject.toml, action.yml, workflows |
| GitHub API client & event parsing | ✅ Complete | httpx, clean IssueEvent objects |
| LLM classification & label application | ✅ Complete | gpt-4o-mini, function calling, retry |
| Missing info detection & comment posting | ✅ Complete | Heuristic field checks, needs-info lifecycle |
| YAML config with zero-config defaults | ✅ Complete | pydantic validation, .github/triagebot.yml |
| README, install docs & marketplace metadata | ✅ Complete | LICENSE, screenshots, marketplace branding |
| Code review | 🚧 In Progress | |
| Publish to GitHub Marketplace | 📋 Planned | |

## How It Works

When someone opens an issue, TriageBot:
1. **Classifies** it into a category (`bug`, `feature-request`, `question`, `documentation`) and applies the matching label
2. **Checks** whether required fields are present (reproduction steps, expected behavior, actual behavior) and posts a comment requesting anything missing

On issue edits, it re-checks the missing fields and removes the `needs-info` label once everything is filled in.

### Classification label applied

> _Screenshot placeholder — shows a newly opened issue with a `bug` label applied within seconds_

![Classification label applied](docs/screenshots/label-applied.png)

### Missing info comment

> _Screenshot placeholder — shows the automated comment listing which required fields are absent, and the `needs-info` label on the issue_

![Missing info comment](docs/screenshots/missing-info-comment.png)

### Auto-resolved after edit

> _Screenshot placeholder — shows the `needs-info` label removed after the reporter filled in the missing fields_

![needs-info removed after edit](docs/screenshots/needs-info-removed.png)

---

## Install

**30-second setup:**

1. Add your OpenAI API key to your repo secrets: **Settings → Secrets and variables → Actions → New repository secret** → name it `OPENAI_API_KEY`

2. Create `.github/workflows/triagebot.yml` in your repo:

```yaml
name: TriageBot

on:
  issues:
    types: [opened, edited]

jobs:
  triage:
    runs-on: ubuntu-latest
    permissions:
      issues: write
    steps:
      - uses: daemonship/triagebot@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

That's it. No infrastructure, no webhooks, no database.

---

## Configuration

TriageBot works with zero configuration out of the box. To customize behavior, create `.github/triagebot.yml` in your repo:

```yaml
classification:
  # Labels to classify issues into.
  # These labels are created on your repo automatically if they don't exist.
  # Default: [bug, feature-request, question, documentation]
  categories:
    - bug
    - enhancement
    - question
    - docs

missing_info:
  # Fields required in all issue reports.
  # TriageBot uses heuristic matching (section headers, bold labels) to detect presence.
  # Default: [reproduction steps, expected behavior, actual behavior]
  required_fields:
    - reproduction steps
    - expected behavior
    - actual behavior
```

See [`.github/triagebot.example.yml`](.github/triagebot.example.yml) for the full annotated reference.

### Config keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `classification.enabled` | boolean | `true` | Set to `false` to disable LLM classification entirely (no API calls, zero cost) |
| `classification.categories` | list of strings | `[bug, feature-request, question, documentation]` | Labels to classify issues into |
| `missing_info.required_fields` | list of strings | `[reproduction steps, expected behavior, actual behavior]` | Fields that must be present in issue body |

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `github-token` | Yes | — | GitHub token with `issues: write` permission (use `secrets.GITHUB_TOKEN`) |
| `openai-api-key` | Yes | — | OpenAI API key for LLM classification |
| `config-path` | No | `.github/triagebot.yml` | Path to config file relative to repo root |

---

## Cost

TriageBot uses `gpt-4o-mini` by default, which costs approximately **$0.00015 per issue classified** (~150 input tokens for the prompt + title/body, 10–20 output tokens for the JSON response).

| Volume | Estimated monthly cost |
|--------|----------------------|
| 100 issues/month | ~$0.015 |
| 1,000 issues/month | ~$0.15 |
| 10,000 issues/month | ~$1.50 |

**To eliminate API costs entirely**, set `classification.enabled: false` in `.github/triagebot.yml`. Missing-info detection continues to work with no API calls:

```yaml
classification:
  enabled: false   # disable LLM classification — no API key needed

missing_info:
  required_fields:
    - reproduction steps
    - expected behavior
    - actual behavior
```

**To use a cheaper or self-hosted model**, set the `base-url` and `model` inputs in your workflow to point to any OpenAI-compatible endpoint (Gemini, DeepSeek, Ollama, etc.).

---

## Reliability & Error Handling

TriageBot is designed to fail safely and leave a clear audit trail in the GitHub Actions log.

### Logging

Every run emits structured log lines with timestamps and log levels, visible in the **Actions** tab of your repository:

```
2024-01-15T10:23:01 [triagebot] INFO Processing opened issue #42: App crashes on login
2024-01-15T10:23:02 [triagebot] INFO Classification: category='bug' confidence=0.94
2024-01-15T10:23:02 [triagebot] INFO Applied label 'bug'
2024-01-15T10:23:02 [triagebot] INFO All required fields present
```

### OpenAI API failures

If the OpenAI API is unreachable or rate-limited, TriageBot:

1. **Retries up to 3 times** with exponential backoff (4 s → 8 s → 16 s) for `RateLimitError`, timeout, and connection errors
2. **Falls back to `needs-triage`** if all retries are exhausted — the issue is labeled for manual review rather than dropped
3. **Logs a warning** with the error message so the failure is visible in the Actions log

Invalid API keys cause an immediate `AuthenticationError` which fails the Action with a clear log message.

### GitHub API failures

If the GitHub API returns a network error (connection refused, timeout, etc.), TriageBot:

1. **Retries up to 3 times** with exponential backoff (2 s → 4 s → 8 s)
2. **Fails the Action** if all retries are exhausted, surfacing the error in the Actions log

HTTP 4xx errors (bad token, missing permissions) are not retried — they fail immediately with a descriptive error.

### If the Action fails

GitHub Actions marks the workflow run as failed and sends an email notification to repository maintainers (based on your notification settings). The full log is available in the **Actions** tab for debugging.

---

## Contributing

1. Fork the repo and create a branch
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Run tests: `pytest -q`
4. Open a pull request

---

## License

[MIT](LICENSE) — © 2026 DaemonShip
