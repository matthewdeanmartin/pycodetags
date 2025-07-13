# PyCodeTags: A Developer's Workflow Guide

This document outlines a workflow for a software developer named Matt, using `pycodetags` and its
`pycodetags-issue-tracker` plugin to manage tasks, bugs, and other metadata directly within the source code. This approach keeps
tasks version-controlled and colocated with the code they affect, minimizing context switching.

## 1. Initial Project Setup

Before Matt can start, he configures his project to use `pycodetags`.

### Installation

First, he installs the necessary packages:

```bash
pip install pycodetags
pip install pycodetags-issue-tracker
```

For advanced users you can use pipx to minimize dependencies installed in your virtual environment.

### Configuration (`pyproject.toml`)

Next, he sets up the `[tool.pycodetags]` section in his `pyproject.toml` file. This configuration defines the rules for
his project's code tags.

```
[tool.pycodetags]
# Tell pycodetags which modules/folders to scan by default
modules = ["my_project"]
src = ["src/"]

# Define what a "done" status means for reporting
closed_status = ["done", "closed", "fixed", "nobug", "wontfix"]

# Define valid values for certain fields to ensure consistency
valid_status = ["planning", "ready", "development", "testing", "done", "closed"]
valid_priorities = ["high", "medium", "low"]
valid_categories = ["core", "ui", "api", "parser", "plugin", "validation", "views"]
valid_releases = ["1.0.0", "1.1.0", "2.0.0"]

# Enforce that certain fields must be present on a tag
mandatory_fields = ["originator", "origination_date", "status", "category", "priority"]

# --- User and Author settings for the issue-tracker ---
# Use git to identify the current user for features like validation
user_identification_technique = "os"

# A list of recognized authors for validation purposes
valid_authors = ["matth", "cle", "jrnewbie"]

```

## 2. The Task Lifecycle: From Idea to Done

This section follows a single task through its entire lifecycle.

### Step 1: Creating a New Task

While working in `src/my_project/parser.py`, Matt discovers a significant bug where the comment parser fails to walk the
entire Abstract Syntax Tree (AST). He immediately documents it as a `BUG` right where he found it.

#### src/my_project/parser.py
```python
def find_comment_blocks_from_string(source: str):
    tree = parse(source)
    lines = source.splitlines()

    # Filter out comment nodes
    # BUG: fails to walk the whole tree. This is shallow. <matth 2025-07-06
    #  category:parser priority:high status:development release:1.0.0>
    comments = [node for node in walk(tree) if isinstance(node, Comment)]
    # ... rest of the function

```

* **`BUG`**: The tag type.

* **`fails to walk...`**: A description of the problem.

* **`<...>`**: The metadata block.

* **`matth 2025-07-06`**: The `originator` and `origination_date` (a default field).

* **`category:parser priority:high ...`**: Other mandatory fields defined in the config.

To see all open issues, Matt can run:

```bash
pycodetags issues --src src/
```

### Step 2: Planning and Assignment

During a team meeting, they decide this bug is critical for the `1.0.0` release. Matt updates the tag to assign it to a
developer named Cle and sets the status to `ready`.

The comment in `src/my_project/parser.py` is now:

```
# BUG: fails to walk the whole tree. This is shallow. <matth 2025-07-06
#  assignee:cle category:parser priority:high status:ready release:1.0.0>

```

### Step 3: Completing the Task

Cle fixes the bug. Before committing his code, he updates the code tag one last time to reflect its completion. This
captures the "who, what, and when" for historical and reporting purposes.

The final tag looks like this:

```
# BUG: fails to walk the whole tree. This is shallow. <matth 2025-07-06
#  assignee:cle category:parser priority:high status:done release:1.0.0
#  change_type:Fixed closed_date:2025-07-06>

```

* **`status:done`**: Marks the task as complete.

* **`change_type:Fixed`**: Specifies the nature of the change for the changelog.

* **`closed_date:2025-07-06`**: Records when the work was finished.

### Step 4: Validation

Before pushing his changes, Cle runs the validation command to ensure all his code tags conform to the project's rules.

```bash
pycodetags issues --format validate
```

If he had forgotten the `release` field on his `done` tag, validation would fail with a helpful message:

```
# BUG: ... <... status:done closed_date:2025-07-06>
/path/to/src/my_project/parser.py:12:3
  Item is done, missing release, suggest ['1.0.0', '1.1.0', '2.0.0']

Original Schema pep350
...
```

This ensures data quality and prevents incomplete records from entering the codebase.

## 3. Reporting and Project Management

With tasks managed in the code, reporting becomes automated.

### Generating a Changelog

At the end of the release cycle, Matt needs to generate release notes. He runs:

```bash
pycodetags issues --format changelog
```

This command finds all tags marked `status:done` for the `1.0.0` release and formats them into a clean changelog file.

**Output (`CHANGELOG.md`):**

```
# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-07-06

### Fixed
- fails to walk the whole tree. This is shallow.

```

### Viewing a Project Board

To get a quick overview of all tasks, Matt can generate a Markdown-based board:

```bash
pycodetags issues --format todomd
```

**Output (`TODO.md`):**

```markdown
# Code Tags TODO Board
Tasks and progress overview.

### ready
- [ ] Some other task ~2025-07-10 #api @jrnewbie

### testing
- [ ] A feature in testing ~2025-07-08 #ui @cle

### done ✓
- [x] fails to walk the whole tree. This is shallow. (2025-07-06)

```

### Generating an HTML Health Report

To get a more visual overview of the project's health, including metrics on bug density and code sentiment, Matt can
generate a full HTML report.

```bash
pycodetags issues --format html
```

This command creates an `issues_site/` directory with an `index.html` file and automatically opens it in his browser,
showing a dashboard with all open and closed issues, plus calculated health metrics.

## 4. Using the Generic `DATA` Tag

Sometimes, Matt needs to store structured data in comments that isn't an issue. For this, he uses the generic `DATA`
tag. This is useful for configuration details, metadata, or notes that should live with the code.

```python
# DATA: Database connection details for the test environment.
#  <host:"test.db.internal" port:5432 user:"test_user">
def connect_to_database():
    ...
```

This data doesn't appear in issue reports but can be extracted for other purposes, like scripting or documentation
generation.

```bash
pycodetags data --format json
```

**Output:**

```json
[
  {
    "code_tag": "DATA",
    "comment": "Database connection details for the test environment.",
    "custom_fields": {
      "host": "test.db.internal",
      "port": "5432",
      "user": "test_user"
    },
    "file_path": "src/my_project/db.py",
    "line_number": 5
  }
]
```
