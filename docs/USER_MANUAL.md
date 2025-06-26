# Code Tags User Manual

## Introduction

`pycodetags` is a Python tool designed to help developers manage and track various types of "code tags" within their
source code. These tags, such as `TODO`, `FIXME`, `BUG`, `DONE`, etc., serve as annotations to highlight areas that
require attention, indicate completed tasks, or mark sections for future work.

This tool supports two main styles of code tags:

1. **Strongly Typed Code Tags:** These are `TODO` and `DONE` objects (and their variations like `FIXME`, `BUG`,
   `WONTFIX`) created directly in Python code using the `pycodetags` library. They allow for rich metadata such as
   assignees, due dates, and tracker URLs.

1. **Folk and PEP-350 Style Code Tags:** These are traditional comment-based tags found in source files (e.g.,
   `# TODO: Fix this bug`). The tool can parse these comments to extract information.

`pycodetags` can generate reports in various formats, including plain text, HTML, JSON, a "Keep a Changelog" format, and
a Markdown-based TODO board.

## Installation

While the provided files do not contain installation instructions, typically, Python packages are installed using `pip`.
Assuming `pycodetags` is a discoverable package, you would install it as follows:

```bash
pip install pycodetags
```

## Basic Usage

The `pycodetags` tool is a command-line utility. You can use it to inspect either a Python module or a directory
containing source code.

### Inspecting a Python Module

To inspect a Python module for strongly typed `TODO` and `DONE` objects:

```bash
pycodetags --module my_project.my_module
```

Replace `my_project.my_module` with the actual importable path to your Python module.

### Inspecting Source Code Files

To inspect a file or a folder of source code for folk and PEP-350 style code tags:

```bash
pycodetags --src path/to/your/code
```

Replace `path/to/your/code` with the path to your source file or directory. If it's a directory, `pycodetags` will
recursively scan all `.py` files within it.

### Combined Usage

You can use both `--module` and `--src` together to collect both types of tags:

```bash
pycodetags --module my_project.my_module --src path/to/your/code
```

## Code Tag Types

`pycodetags` recognizes and categorizes different types of annotations within your codebase.

### Strongly Typed Tags (Python Objects)

These tags are instances of the `TODO` class (or its specialized factories) defined in `pycodetags.main_types`. They
offer a structured way to add detailed metadata.

- **`TODO(...)`**: The general-purpose tag for tasks that need to be done.

  - **Parameters:**

    - `code_tag` (str, optional): The type of tag (e.g., "TODO", "FIXME", "BUG"). Defaults to "TODO".

    - `assignee` (str, optional): Who is responsible for this task. Defaults to "unknown".

    - `comment` (str): A description of the task. Defaults to "Not implemented".

    - `origination_date` (str, optional): Date the tag was created.

    - `due` (str, optional): Due date in `YYYY-MM-DD` format.

    - `release_due` (str, optional): Release by which the task should be completed.

    - `change_type` (str, optional): For `DONE` tags, describes the nature of the change (e.g., "Added", 
       "Changed", "Fixed").

    - `closed_date` (datetime.datetime, optional): Date the task was marked as done.

    - `tracker` (str, optional): URL to an issue tracker ticket.

    - `file_name` (str, optional): The file where the tag is located.

    - `line_number` (int, optional): The line number where the tag is located.

- **`DONE(...)`**: Marks a task as completed. It's a specialized `TODO` with `code_tag="DONE"`.

- **`NOBUG(...)`**: Indicates that an item initially thought to be a bug was not a problem after all.

- **`WONTFIX(...)`**: Denotes a task that was investigated but decided not to be implemented.

- **`REQUIREMENT(...)`**: A variation of `TODO` for requirements.

- **`STORY(...)`**: Another variation of `TODO` for user stories.

- **`IDEA(...)`**: For ideas or potential future enhancements.

- **`FIXME(...)`**: Specifically for code that is broken and needs fixing.

- **`BUG(...)`**: Similar to `FIXME`, indicating a bug.

- **`HACK(...)`**: For code that is a workaround and should be refactored.

- **`CLEVER(...)`**: Marks sections of code that might be overly clever or hard to understand, potentially needing
  simplification.

- **`MAGIC(...)`**: For "magic" code (code that works but its mechanism isn't immediately obvious).

- **`ALERT(...)`**: An urgent `TODO`.

- **`PORT(...)`**: Indicates code that needs to be made compatible with more environments.

- **`DOCUMENT(...)`**: Highlights areas where documentation needs to be added.

**Usage as Decorator:**
`TODO` objects can also be used as decorators to mark functions or methods:

```python
from pycodetags import TODO


@TODO(assignee="John Doe", comment="Refactor this function for better performance", due_date="12/31/2025")
def my_function():
    # ... function code ...
    pass
```

### Folk Schema Tags (Comment-based)

These are traditional comments following a less strict structure. They generally start with `# TAG: comment` or
`# TAG(field): comment`.

**Examples:**

- `# TODO: Implement authentication`

- `# TODO(user): Update error handling`

- `# FIXME(ticket-123): This loop causes an infinite recursion`

- `# BUG: Crashes if run on Sundays. <MDE 2005-09-04 d:14w p:2>`

The tool attempts to extract `code_tag`, `default_field`, `custom_fields`, and `comment` from these. It can also
identify URLs within comments as a `tracker`.

### PEP-350 Style Code Tags (Comment-based)

These follow a more structured comment format based on PEP-350:

`# TAG: comment <field_string>`

The `field_string` can contain key-value pairs or positional values.

**Examples:**

- `# FIXME: Seems like this Loop should be finite. <MDE, CLE d:14w p:2>`

-

`# TODO: This is a complex task that needs more details. <assignee=JRNewbie priority:3 due=2025-12-25 custom_field: some_value>`

- `# RFE: Add a new feature for exporting. <assignee:Micahe,CLE priority=1 2025-06-15>`

**Supported Fields in `field_string`:**

- **Aliases:** `p` (priority), `d` (due), `t` (tracker), `s` (status), `c` (category), `i` (iteration), `r` (release),
  `a` (assignee).

- **Full Names:** `priority`, `due`, `tracker`, `status`, `category`, `iteration`, `release`, `assignee`, `originator`.

- **Special:** Date format `YYYY-MM-DD` (e.g., `2024-12-31`), week format `Nw` (e.g., `14w`), initials (e.g., `MDE`).

## Output Formats

The `--format` argument allows you to specify how the collected code tags are presented.

- **`--format text` (Default):**
  Prints a simple text-based report to the console, listing TODOs, Dones, and any `TodoException`s found.

  ```
  --- TODOs ---
  TODO(assignee='Matth', due_date='None', comment='ATTR Intellisense for class aliases (DONE, FIXME, etc) is broken 2', severity='None', change_type='Added', tags=[])
  ...

  --- Dones ---
  No Dones found.

  --- Exceptions ---
  No Dones found.

  ```

- **`--format html`:**
  Generates an HTML report, suitable for viewing in a web browser.

  ```html
  <h1>Dones</h1>
  <ul>
      <li><strong>Comment for done task</strong><br>Author: assignee_name<br>Close: 2024-01-01</li>
  </ul>
  <h1>TODOs</h1>
  <ul>
      <li><strong>Comment for todo task</strong><br>Assignee: assignee_name<br>Due: 12/31/2025</li>
  </ul>
  <h1>TODO Exceptions</h1>
  <ul>
      <li><strong>Exception message</strong><br>Assignee: assignee_name<br>Due: 12/31/2025</li>
  </ul>

  ```

- **`--format json`:**
  Outputs the collected data in a structured JSON format. This is useful for programmatic processing.

  ```json
  {
    "todos": [
      {
        "code_tag": "TODO",
        "comment": "ATTR Intellisense for class aliases (DONE, FIXME, etc) is broken 2",
        "assignee": "Matth",
        "tracker": null,
        "created_on": null,
        "due_date": null,
        "version_due": "0.5.0",
        "version_done": null,
        "release_due": null,
        "closed_date": null,
        "change_type": "Added",
        "file_name": "own_todos.py",
        "line_number": 10
      }
      // ... more todos and other tag types
    ],
    "dones": [],
    "exceptions": []
  }

  ```

- **`--format keep-a-changelog`:**
  Generates a changelog specifically from `DONE` tags that have a `version_done` defined, formatted according to the "
  Keep a Changelog" specification.

  ```markdown
  # Changelog

  All notable changes to this project will be documented in this file.

  ## [0.5.0] - 2024-06-20

  ### Fixed
  - Fixed issue with intellisense ([ISSUE-123](https://example.com/ISSUE-123))

  ...

  ```

- **`--format todo.md`:**
  Outputs a markdown-based TODO board, which can be useful for visualization in markdown-compatible editors or
  platforms.

  ```markdown
  # Code Tags TODO Board
  Tasks and progress overview.

  ### TODOs
  - [ ] ATTR Intellisense for class aliases (DONE, FIXME, etc) is broken 2 ~0.5.0 #added @Matth
  - [ ] CLASS Intellisense for class aliases (DONE, FIXME, etc) is broken 2 ~0.5.0 #added @Matth
  - [ ] EMTHOD Intellisense for class aliases (DONE, FIXME, etc) is broken 2 ~0.5.0 #added @Matth

  ### Completed Column
  - [x] Completed task example (2024-01-01)

  ```

## Configuration

`pycodetags` uses `dynaconf` for configuration, looking for settings in `settings.toml` and `.secrets.toml` files, and
environment variables prefixed with `pycodetags_`.

Key configurable settings (as inferred from `config.py` and `main_types.py`):

- **`REQUIRE_tracker`**: If `True`, a `tracker` URL must be provided for `TODO` items.

- **`REQUIRE_DUE_DATE`**: If `True`, `due_date` or `version_due` must be provided for `TODO` items that are not marked
  as `DONE`, `NOBUG`, or `WONTFIX`.

- **`SHIFT_DATES_BY`**: Allows shifting due dates by a specified amount (e.g., "10d" for 10 days, "1m" for 1 month, "1y"
  for 1 year).

- **`ACTION`**: Defines an action to take when a `TODO` condition is met (e.g., past due date, assignee matches current
  user).

  - `"stop"`: Raises a `TodoException`, effectively stopping execution.

  - `"warn"`: Issues a Python warning.

  - `"nothing"` (default): No action is taken.

- **`ACTION_ON_PAST_DUE`**: If `True`, trigger `ACTION` when `due_date` is in the past.

- **`ACTION_ON_USER_MATCH`**: If `True`, trigger `ACTION` when `assignee` matches the current user.

- **`USER_IDENTIFICATION`**: How to determine the current user.

  - `"git"`: Uses `git config user.name`.

  - `"env"`: Uses the environment variable specified by `USER_ENV_VAR` (e.g., `pycodetags_USER`).

  - `"os"` (default): Uses `USER` or `USERNAME` environment variables.

- **`USER_ENV_VAR`**: The environment variable to check for user identity if `USER_IDENTIFICATION` is set to `"env"`.

## Error Handling

- **`TodoException`**: This custom exception is raised when a `TODO`'s conditions (e.g., past due, assigned to current
  user) are met and the `ACTION` setting is configured to `"stop"`.

- **`ImportError`**: If `--module` specifies a module that cannot be imported, the tool will print an error message and
  exit.

- **`ValueError`**: Raised if required fields (like `tracker` or `due_date`) are missing based on configuration
  settings.

- **`FileNotFoundError`**: If `--src` points to a non-existent file or directory.

## Logging

The tool uses Python's standard logging.

- By default, it operates in a quiet mode, only logging `FATAL` errors.

- To enable more verbose output (including `DEBUG` level messages), use the `--verbose` flag. This can be helpful for
  debugging or understanding the tool's internal workings.
