# TriageBot

Automatically classify GitHub issues and request missing information — powered by `gpt-4o-mini`.

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
| README, install docs & marketplace metadata | 🚧 In Progress | |
| Code review | 📋 Planned | |
| Publish to GitHub Marketplace | 📋 Planned | |

When someone opens an issue, TriageBot:
1. Classifies it into a category (`bug`, `feature-request`, `question`, `documentation`) and applies the matching label
2. Checks whether required fields are present (reproduction steps, expected behavior, actual behavior) and posts a comment requesting anything missing

On issue edits, it re-checks the missing fields and removes the `needs-info` label once everything is filled in.

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

## Usage

Once installed, TriageBot runs automatically on every new issue and every issue edit. You don't need to do anything.

**What you'll see:**
- New issues get a category label (`bug`, `feature-request`, etc.) if the classification is confident, or `needs-triage` if it's ambiguous
- Issues missing required information get a `needs-info` label and a comment listing what's needed
- When an issue is edited to include the missing info, `needs-info` is automatically removed

## Configuration

TriageBot works with zero configuration. To customize, create `.github/triagebot.yml`:

```yaml
classification:
  categories:
    - bug
    - enhancement
    - question
    - docs

missing_info:
  required_fields:
    - reproduction steps
    - expected behavior
    - actual behavior
```

See [`.github/triagebot.example.yml`](.github/triagebot.example.yml) for the full reference.

## Cost

TriageBot uses `gpt-4o-mini`, which costs ~$0.00015 per issue. A repo receiving 1,000 issues/month spends about **$0.15**.

## License

MIT
