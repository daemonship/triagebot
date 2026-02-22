# TriageBot Configuration Guide

This guide provides comprehensive documentation for all TriageBot configuration options.

## Quick Start

TriageBot works out of the box with zero configuration. Simply add the workflow file and you're ready to go.

## Configuration File

To customize behavior, create `.github/triagebot.yml` in your repository:

```yaml
classification:
  enabled: true
  categories:
    - bug
    - feature-request
    - question
    - documentation

missing_info:
  required_fields:
    - reproduction steps
    - expected behavior
    - actual behavior
```

## Configuration Reference

### `classification`

Controls how TriageBot classifies issues using LLM.

#### `classification.enabled`

- **Type**: `boolean`
- **Default**: `true`
- **Description**: Enable or disable LLM-based issue classification. When disabled, TriageBot will only perform missing-info detection without making any API calls, reducing cost to zero.

**Example - Disable classification:**
```yaml
classification:
  enabled: false  # No API calls, zero cost
```

#### `classification.categories`

- **Type**: `list of strings`
- **Default**: `["bug", "feature-request", "question", "documentation"]`
- **Description**: Labels to classify issues into. These labels will be created automatically in your repository if they don't exist.

**Example - Custom categories:**
```yaml
classification:
  categories:
    - bug
    - enhancement
    - question
    - docs
    - performance
```

**Notes:**
- Categories must not be empty
- Values are normalized to lowercase
- Use label names that match your project's workflow

---

### `missing_info`

Controls the missing information detection feature.

#### `missing_info.required_fields`

- **Type**: `list of strings`
- **Default**: `["reproduction steps", "expected behavior", "actual behavior"]`
- **Description**: Fields that must be present in issue reports. TriageBot uses heuristic matching (section headers, bold labels) to detect whether each field is present.

**Example - Minimal requirements:**
```yaml
missing_info:
  required_fields:
    - description
```

**Example - Comprehensive requirements:**
```yaml
missing_info:
  required_fields:
    - description
    - steps to reproduce
    - expected behavior
    - actual behavior
    - environment
    - logs
```

**Notes:**
- Field matching is case-insensitive
- TriageBot looks for field names as section headers or bold labels
- Empty field list is allowed (disables missing-info checks)

---

## Configuration Scenarios

### Scenario 1: Zero-Cost Operation

Disable LLM classification to eliminate API costs while still benefiting from missing-info detection:

```yaml
classification:
  enabled: false

missing_info:
  required_fields:
    - description
    - steps to reproduce
    - expected behavior
```

### Scenario 2: Minimal Bug Tracker

Simple setup for small projects:

```yaml
classification:
  categories:
    - bug
    - enhancement

missing_info:
  required_fields:
    - description
```

### Scenario 3: Enterprise Issue Management

Comprehensive setup for larger projects:

```yaml
classification:
  categories:
    - bug
    - feature
    - enhancement
    - documentation
    - security
    - performance

missing_info:
  required_fields:
    - description
    - steps to reproduce
    - expected behavior
    - actual behavior
    - environment details
    - logs or screenshots
```

### Scenario 4: Documentation-Focused Project

For projects that primarily need documentation improvements:

```yaml
classification:
  categories:
    - docs
    - typo
    - broken-link
    - unclear

missing_info:
  required_fields:
    - page url
    - issue description
```

---

## Environment Variables

### `TRIAGEBOT_CONFIG_PATH`

- **Default**: `.github/triagebot.yml`
- **Description**: Override the default configuration file path relative to the repository root.

This is primarily useful for testing or multi-environment setups.

---

## Validation

TriageBot validates your configuration on startup. Common validation errors:

- **Empty categories list**: `classification.categories must not be empty`
- **Invalid YAML**: Syntax errors in your configuration file

If validation fails, TriageBot will exit with a clear error message showing what needs to be fixed.

---

## Troubleshooting

### Configuration not being applied

1. Ensure the file is located at `.github/triagebot.yml`
2. Check YAML syntax is valid
3. Verify the workflow has access to the configuration file

### Labels not being created

TriageBot automatically creates labels defined in `classification.categories`. Ensure:
- The `GITHUB_TOKEN` has `issues: write` permission
- Labels don't conflict with protected system labels

### Required fields not detected

TriageBot uses heuristic matching. For best results:
- Use clear section headers: `## Steps to Reproduce`
- Or bold labels: `**Expected Behavior:**`
- Field names are case-insensitive but should match conceptually

---

## See Also

- [Example configuration](.github/triagebot.example.yml) - Annotated example file
- [Action inputs](../README.md#inputs) - Workflow configuration options
- [Cost estimation](../README.md#cost) - API cost breakdown
