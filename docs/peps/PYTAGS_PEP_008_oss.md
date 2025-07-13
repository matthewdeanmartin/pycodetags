# PYCODETAGS PEP: Open Source Contributor Workflow for `pycodetags-issue-tracker`

| PEP:             | 007                                                                               |
|------------------|-----------------------------------------------------------------------------------|
| Title:           | Open Source Methodology for `pycodetags-issue-tracker` Plugin                     |
| Author:          | Matthew Martin [matthewdeanmartin@gmail.com](mailto\:matthewdeanmartin@gmail.com) |
| Author:          | ChatGPT (gpt-4-turbo, OpenAI)                                                     |
| Status:          | Draft                                                                             |
| Type:            | Standards Track                                                                   |
| Created:         | 2025-07-12                                                                        |
| License:         | MIT                                                                               |
| Intended Version | ≥ 0.6.0                                                                           |



## Abstract

This proposal defines a tagging schema and workflow suitable for open source software (OSS) development using the `pycodetags-issue-tracker` plugin. It models the organic, volunteer-driven nature of OSS by emphasizing flexibility, labels, and contribution metadata rather than deadlines or sprints.

---

## Motivation

Open source projects typically:

* Are maintained by multiple casual or semi-regular contributors
* Do not operate in sprints or planned iterations
* Use labels (e.g., `good first issue`, `help wanted`) to guide contributor engagement
* Avoid assigning due dates or firm priorities
* Track issues using natural language status and label metadata

This methodology aligns the issue tracker with these expectations and GitHub-style workflows.

---

## Specification

### Supported Fields

| Field Name     | Type | Description                                                |
| -------------- | ---- | ---------------------------------------------------------- |
| `comment`      | str  | Required short summary                                     |
| `status`       | str  | Flexible text status (`open`, `closed`, `in-review`, etc.) |
| `label`        | list | List of GitHub-style labels (`bug`, `enhancement`, etc.)   |
| `originator`   | str  | User who reported or introduced the item                   |
| `implementer`  | str  | User who implemented or closed the item                    |
| `closed_date`  | date | Date the issue was resolved                                |
| `release`      | str  | Release version included in, typically filled post-close   |
| `pull_request` | str  | Optional link to the PR that implemented the work          |

### Optional Standard Labels

* `good first issue`
* `help wanted`
* `enhancement`
* `bug`
* `documentation`
* `discussion`

These should be encouraged but not enforced.

---

## Validation Notes

Compared to PEP350 or Scrum-based schemas:

* No `due` field is used
* No `assignee` or `iteration`
* No velocity, story points, or planning fields
* Validation checks:

  * `comment` is required
  * `label` must be non-empty for `open` items (optional rule)
  * `release` and `closed_date` are expected when `status = closed`

---

## Reports

### 1. `label-index`

Groups and lists all tags by their labels (e.g., all `good first issue` tags).

### 2. `unreleased`

Finds closed issues without an associated `release` version.

### 3. `pull-requests`

Lists items with a `pull_request` link for changelog or crediting contributors.

### 4. `contributions`

Groups tags by `implementer` to show contributor summaries.

### 5. `validate`

Ensures presence of required fields (`comment`, `label`, etc.) and basic correctness.

---

## Configuration Example

```toml
[tool.pycodetags.issue_tracking]
schema = "opensource"

[tool.pycodetags.opensource]
valid_labels = ["bug", "enhancement", "good first issue", "documentation"]
mandatory_fields = ["comment", "status"]
require_label_for_open = true
```

---

## Summary

This PEP defines an issue tracker schema suited to open source projects:

* Relies on label metadata for discoverability
* Removes deadline-based tracking
* Emphasizes contributor identity and public activity (e.g., pull requests)

It provides familiar GitHub-compatible semantics while enabling in-repo tracking of issues and contributions for open source maintainers and volunteers.
