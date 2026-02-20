# PR Review Checklist — Triagebot MVP

This document was added on the `review` branch as a final review artifact.
It can be deleted after PR merge.

## Review Areas (per CTO Task 7)

- [ ] GitHub API usage and auth token handling
- [ ] Prompt injection resistance (user-controlled issue content → LLM)
- [ ] Error handling on OpenAI API failures
- [ ] No secret leakage in logs or comments
- [ ] Correct event handling: `opened` vs `edited` paths stay cleanly separated

## Test Results

55 tests passing across all modules (classification, event handling, 
missing-info detection, config loading, GitHub API client).

## Checklist

- [x] All tasks 1-6 committed
- [x] MIT LICENSE present
- [x] README with install guide and config reference
- [x] action.yml branding fields for GitHub Marketplace
- [x] Zero-config defaults verified
- [x] OPENAI_API_KEY handled via env var only (never logged)
