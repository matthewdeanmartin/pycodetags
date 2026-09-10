# pycodetags

Store structured data in Python comments, next to the code it describes.

pycodetags grew out of PEP-350 and the many homegrown ways people write TODOs in
code comments: a label, a description, perhaps an owner or a deadline. It generalizes
that idea into a library for reading, writing, and querying comment records.

Use it for tasks, requirements, design notes, or metadata that your own tools consume.
The core handles the records; your application decides what they mean.

```python
# DATA: Customer export policy
# owner=analytics retention_days=30
# Remove generated exports after their retention period.
def export_customers():
    pass
```

That comment contains a tag (`DATA`), a title, named properties, and a body. It stays
readable in the source file while also being available as data to Python programs.

## Install

```shell
pip install pycodetags
```

Supports Python 3.9–3.15. For command-line use in a separate environment:

```shell
pipx install pycodetags
```

## Read and write records

This example uses TDG, one of the built-in comment formats:

```python
from dataclasses import replace
from pycodetags import loads, dumps

record = loads(
    "# DATA: Customer export policy\n"
    "# owner=analytics retention_days=30\n"
    "# Remove generated exports after their retention period.\n",
    schema="TDG",
)

print(record.title)                            # Customer export policy
print(record.custom_fields["retention_days"])  # "30" (a string)

updated = replace(record, title="Customer export retention policy")
print(dumps(updated))
```

Properties are read as strings. The library preserves custom properties; it doesn't
apply your application's business rules or perform actions described by a comment.
`loads` reads one record; `loads_all` reads multiple records.

## Work with source files

Choose a schema and the source folders in your project's `pyproject.toml`:

```toml
[tool.pycodetags]
schema = "TDG"
src = ["src"]
```

Replace `src` with your Python source folder. Save the opening example as
`src/exports.py`, then inspect it from Python:

```python
from pycodetags import inspect_file

for record in inspect_file("src/exports.py"):
    print(record.code_tag, record.title, record.custom_fields)
```

Or collect the project's records as JSON:

```shell
pycodetags data --format json
```

Select the schema in configuration or pass `schema=` to the API. The library does
not guess which convention an unfamiliar comment uses.

## Comment formats

TDG puts properties immediately after the title, followed by the description:

```python
# TODO: Explain invalid dates
# assignee=alice priority=high
# Include the row number in the error message.
```

Extended PEP-350 puts properties in a closing metadata block:

```python
# TODO: Explain invalid dates
# Include the row number in the error message.
# <assignee=alice priority=high>
```

Use `schema = "PEP350"` to read the second form. In both formats, the first line
supplies the title and subsequent description lines supply the body. A PEP-350 tag
ends at its closing `>`; a TDG tag ends at a non-comment line, another recognized
tag, or the end of the file.

Both built-in schemas recognize tags such as `TODO`, `BUG`, `NOTE`, `REQ`, and `DATA`.
You can also define a schema with your own tag names and fields. See the
[core reference](spec/core_reference.md) for custom schemas, quoting, multiline
comments, and projects that use different formats in different files.

## Edit records in place

Use records read from a source file to update or delete its comments:

```python
from dataclasses import replace
from pycodetags import inspect_file, update_tags

path = "src/exports.py"
record = inspect_file(path)[0]
updated = replace(record, title="Customer export retention policy")
update_tags(path, [(record, updated)])
```

`delete_tags` removes selected records; `apply_mutations` combines updates and deletes
in one file. Edits preserve surrounding code and reject records read before the file
changed. Read the file again before making another batch of edits. Writes require
one writer at a time; they are not transactions across multiple source files.

## Repeated queries

For repeated lookups, build a SQLite snapshot of the configured source folders:

```python
from pathlib import Path
from pycodetags import TagIndex

index = TagIndex(Path("."))
index.refresh()
records = index.query_snapshot(file_path="src/exports.py")
```

Queries read the last refreshed snapshot. Call `refresh()` after changing source
files. Refresh reads the selected files but reparses only changed files; the source
remains authoritative. See the [core reference](spec/core_reference.md) for scan
exclusions, local IDs, and lookups by ID or tracker URL.

## Task reports

For task validation and text, HTML, and changelog reports, install the
[issue-tracker plugin](plugins/pycodetags_issue_tracker/README.md):

```shell
pip install pycodetags-issue-tracker
pycodetags issues --format text
```

Plugins can provide schemas and application-specific behavior. The core library
can be used on its own.

## More information

- [Core reference](spec/core_reference.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Report a bug](https://github.com/matthewdeanmartin/pycodetags/issues)
