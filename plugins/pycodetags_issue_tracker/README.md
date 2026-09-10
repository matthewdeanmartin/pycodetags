# pycodetags Issue Tracker

Keep TODOs and bugs next to the code they describe, then collect them into a report.
`pycodetags-issue-tracker` adds the `pycodetags issues` command for browsing tasks,
checking their metadata, and generating an HTML report.

## Install

```shell
pip install pycodetags-issue-tracker
```

This installs the required `pycodetags` core too. Requires Python 3.9 or later.

If you installed `pycodetags` with pipx, add the plugin to the same environment:

```shell
pipx inject pycodetags pycodetags-issue-tracker
```

## Quick start

Choose the comment format in your project's `pyproject.toml`. This example uses TDG:

```toml
[tool.pycodetags]
schema = "TDG"
src = ["src"]
```

Replace `src` with the folder containing your Python code. Add a task to a source file:

```python
# TODO: Explain invalid dates in the import error
# priority=high status=todo
# Include the row number and the value that could not be parsed.
def import_rows(rows):
    pass
```

The first line is the title, the next line holds task properties, and the remaining
comment text describes the work.

Run this from the project directory to list your tasks:

```shell
pycodetags issues --format text
```

To generate a browsable report:

```shell
pycodetags issues --format html --output issues_site
```

The report is written to `issues_site/index.html`. Outside CI, the command also
tries to open it in your browser.
For CI or other unattended runs, set `PYCODETAGS_NO_OPEN_BROWSER=1`.

## Other reports

```shell
# Check task metadata; exits with a nonzero status when issues are found.
pycodetags issues --format validate

# Write a Markdown task list.
pycodetags issues --format todomd > TODO.md

# Draft a changelog from completed tasks.
pycodetags issues --format changelog > CHANGELOG_DRAFT.md
```

Use `--src path/to/code` to scan a different file or folder, or `--help` to see
all command options.

## Close a task

Add a `closed_date` to mark a task as completed:

```python
# TODO: Explain invalid dates in the import error
# closed_date=2026-09-10 assignee=matth release=1.0.0 change_type=Fixed
```

Alternatively, list your completed statuses under `[tool.pycodetags]`:

```toml
closed_status = ["done", "closed"]
```

With that setting, `status=done` or `status=closed` marks a task as completed,
even without a closing date. A status name alone has no built-in completion meaning.
These fields describe the task in your source code; they do not close an external
issue-tracker ticket.

The validator requires completed tasks to have an `assignee`, `closed_date`,
`release`, and valid `change_type`. A task can appear as completed in a report
while still failing validation for missing details.

For changelog entries, include `release` and `change_type`. The supported categories
are `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, and `Security`.
Run `--format validate` before generating the draft to catch invalid or missing
categories. The draft retains these entries under `Unclassified`; missing releases
appear under `N/A`. Review the generated draft before publishing it.

## Prefer PEP-350 comments?

Set `schema = "PEP350"` in the same configuration and put task properties between
angle brackets:

```python
# TODO: Explain invalid dates in the import error <priority=high status=todo>
```

The reporting commands are the same for either format.

## Links

- [Documentation](https://pycodetags.readthedocs.io/en/latest/)
- [Source code](https://github.com/matthewdeanmartin/pycodetags)
- [Report a bug](https://github.com/matthewdeanmartin/pycodetags/issues)
- [PyPI](https://pypi.org/project/pycodetags-issue-tracker/)
