# PYCODETAGS PEP: Scrum Support Extension for `pycodetags-issue-tracker` Plugin


| PEP:             | 006                                                                               |
|------------------|-----------------------------------------------------------------------------------|
| Title:           | Textbook Scrum Support for `pycodetags-issue-tracker` Plugin                      |
| Author:          | Matthew Martin [matthewdeanmartin@gmail.com](mailto\:matthewdeanmartin@gmail.com) |
| Author:          | ChatGPT (gpt-4-turbo, OpenAI)                                                     |
| Status:          | Draft                                                                             |
| Type:            | Standards Track                                                                   |
| Created:         | 2025-07-12                                                                        |
| License:         | MIT                                                                               |
| Intended Version | ≥ 0.6.0                                                                           |



## Abstract

This proposal outlines the required fields, reports, validation rules, and configuration extensions necessary to support **Scrum-aligned workflows** using the `pycodetags-issue-tracker` plugin. This will enable pycodetags to support structured agile development workflows natively within the codebase.

---

## Motivation

While the current plugin supports general-purpose issue tracking (TODOs, BUGs, REQUIREMENTs), Scrum requires:

* Explicit task state
* Sprint-based planning
* Backlog grooming
* Definition of Done enforcement
* Team-role distinction (developer vs tester)

Adding Scrum-specific support will enable teams to manage their sprint processes entirely within their repositories and automation.

---

## Specification

### New Fields (Minimal Scrum Schema)

The following additional fields will be added to the `IssueTrackerSchema` variant for Scrum:

| Field Name            | Type | Description                                                     |
| --------------------- | ---- | --------------------------------------------------------------- |
| `story_points`        | int  | Effort estimate for sprint capacity planning                    |
| `acceptance_criteria` | str  | Text description of how to verify task is complete              |
| `epic`                | str  | Optional feature grouping                                       |
| `sprint_goal`         | str  | Purpose of the sprint (may be redundant if captured externally) |

### Scrum Role Support

A new role metadata field will be used only for `developer` and `tester` roles. These are the roles that perform tracked work. Product Owners and Scrum Masters are assumed to be configuration-level concerns, not associated with each task individually.

```toml
[tool.pycodetags.scrum.roles]
jane = "developer"
joe = "tester"
```

### Minimal Statuses and Allowed Transitions

| Status        | Description                       |
|---------------|-----------------------------------|
| `planned`     | In the sprint backlog             |
| `in-progress` | Actively being worked on          |
| `review`      | Done, pending peer/tester review  |
| `blocked`     | Blocked by an external dependency |
| `done`        | Meets the Definition of Done      |

Allowed status transitions:

* `planned` → `in-progress`, `blocked`
* `in-progress` → `review`, `done`, `blocked`
* `review` → `done`, `in-progress`
* `blocked` → `planned`, `in-progress`
* `done` → *(terminal state)*

These will be validated in the CLI (not enforced in editor-level tooling).

---

## Required Reports

These reports will support sprint planning and review:

### 1. `sprint-board`

Kanban-style view: items grouped by `status`, filtered by `iteration`. Optional columns for `assignee`, `story_points`, `due`.

### 2. `sprint-summary`

Aggregates sprint progress:

* Total stories
* Completed stories
* Velocity (`story_points`)
* Incomplete or blocked items

### 3. `backlog-review`

Highlights metadata issues in backlog:

* Missing `story_points`, `epic`, or `assignee`
* Invalid or inconsistent `status`

### 4. `definition-of-done-check`

Lists `status=done` items missing:

* `closed_date`
* `release`
* `change_type`
* Optional: missing `acceptance_criteria`

### 5. `velocity-history` (optional)

Trends velocity over previous iterations using `story_points`.

Note: Not all reports are applicable to all `IssueTrackerSchema` variants. The app must now support **multiple schemas**, and **report applicability must be schema-aware**.

---

## Configuration Extensions

### Indicating Methodology

Support should be added to `pyproject.toml` or config files to declare the active methodology/schema:

```toml
[tool.pycodetags.issue_tracking]
schema = "scrum"
```

### Role Assignment

```toml
[tool.pycodetags.scrum.roles]
jane = "developer"
joe = "tester"
```

### Optional Valid Values

```toml
[tool.pycodetags.scrum]
valid_epics = ["auth", "dashboard", "search"]
valid_iterations = ["Sprint-24", "Sprint-25"]
mandatory_fields = ["story_points", "status", "assignee"]
```

These will be used to validate tags during linting or `--format=validate` CLI runs.

---

## Out of Scope

* Slack or notification integration
* Workflow visualization UI
* Product Owner or Scrum Master tagging per item
* GitHub or CI status integration

These could be added via external integrations or extensions but are not core to the plugin.

---

## Summary

This PEP introduces structured support for Scrum-based tracking with minimal overhead:

* Defines a Scrum-specific schema variant
* Adds role, sprint, and velocity support
* Enhances validation and reporting
* Keeps configuration extensible and opt-in

This will allow pycodetags to scale from informal TODO tracking to structured agile development with minimal friction.
