# PYCODETAGS PEP: Solo Developer Workflow for `pycodetags-issue-tracker`



| PEP:             | 007                                                                               |
|------------------|-----------------------------------------------------------------------------------|
| Title:           | Solo Developer Methodology for `pycodetags-issue-tracker` Plugin                  |
| Author:          | Matthew Martin [matthewdeanmartin@gmail.com](mailto\:matthewdeanmartin@gmail.com) |
| Author:          | ChatGPT (gpt-4-turbo, OpenAI)                                                     |
| Status:          | Draft                                                                             |
| Type:            | Standards Track                                                                   |
| Created:         | 2025-07-12                                                                        |
| License:         | MIT                                                                               |
| Intended Version | ≥ 0.7.0                                                                           |



## Abstract

This proposal defines a minimal and focused workflow for individual developers using `pycodetags-issue-tracker` without team-based structures. It simplifies metadata and reporting by removing all fields and features related to collaboration, roles, and formal sprint planning.

---

## Motivation

Many users of `pycodetags` are solo developers working on personal projects, prototypes, or research. These workflows:

* Don’t involve team roles or assignments
* Rarely use sprints or formal releases
* Prefer fast and lightweight tagging

This methodology defines a lean set of fields and validation rules tailored to these users, enabling clarity and momentum without process overhead.

---

## Specification

### Removed Concepts

The following features are **not included** in this methodology:

* Roles (`assignee`, `originator`, `tester`, etc.)
* Iterations / Sprints
* Product Owner / Scrum Master
* Story points, velocity, capacity planning
* Team validation (e.g., valid authors)

---

## Supported Fields

| Field Name    | Type | Description                              |
|---------------|------|------------------------------------------|
| `comment`     | str  | Required short summary of task           |
| `due`         | date | Optional personal deadline               |
| `status`      | str  | Suggested: `todo`, `in-progress`, `done` |
| `priority`    | str  | Optional: `low`, `medium`, `high`        |
| `category`    | str  | Optional custom grouping                 |
| `release`     | str  | Optional version or milestone name       |
| `closed_date` | date | Optional completion date                 |

### Status Options

A minimal and flexible set of status values:

* `todo`
* `in-progress`
* `done`

These statuses are not enforced, only suggested for consistency.

---

## Reports

Solo developers benefit from simple progress tracking. Suggested supported reports:

### 1. `text`

Default readable format for all tracked items.

### 2. `todomd`

Markdown task list grouped by `status`, optionally sorted by `priority` or `due` date.

### 3. `donefile`

Chronological list of completed items.

### 4. `validate`

Highlights structural issues (e.g., missing comment or invalid date).

### 5. `changelog`

Optionally groups completed items by `release`.

---

## Configuration Example

```toml
[tool.pycodetags.issue_tracking]
schema = "solo"

[tool.pycodetags.solo]
valid_status = ["todo", "in-progress", "done"]
valid_priorities = ["low", "medium", "high"]
mandatory_fields = ["comment"]
```

---

## Summary

This PEP introduces a lightweight and intuitive workflow schema for solo developers:

* Removes team-based fields and complexity
* Focuses on tracking, prioritizing, and completing personal work
* Supports clarity and momentum through clean tags and simple reports

The solo schema encourages adoption of `pycodetags` by individuals without requiring them to adopt organizational processes.
