# pycodetags

You've seen `# TODO:` comments? What if they could be used as an issue tracker?

What if `# TODO:` style comments could serialize and deserialize records, turning comments into a database?

[Live example](https://matthewdeanmartin.github.io/pycodetags/).


[//]: # (What if you could also write comments as decorators that warn or stop you on the due date?)

[//]: # ()
[//]: # (Replace or complement your `# TODO:` comments with decorators similar to NotImplement, Deprecated or Warning)

[//]: # (and get issue tracker features, too.)

Lightweight and keeps your issue tracker in your code.

Backwards compatible with folk `# TODO:` comments, which can vary greatly in how people write them.

Core library is for Data Tags, which are abstract and domain free. Plugs have domain-specific tags, e.g. Issue Tracking.

## Installation

For generic code tags strictly in comments (DATA tags):

`pipx install pycodetags`

For code tag decorators, objects, exceptions, context managers with run-time behavior:

`pip install pycodetags`

To get a domain specific data tags (TODO tags), e.g. issue tracker or discussion, install with plugin

`pip install pycodetag pycodetags-issue-tracker`

Requires python 3.7+. 3.7 will probably work.

The only dependencies are `pluggy` and `ast-comments` and backports of python standard libraries to support old versions
of python. For pure-comment style code tags, pipx install and nothing is installed with your application code.

## Usage

`pycodetags` can work with pre-existing comment based code tags, both the folk-schema style and the PEP-350 style.

Ways to track a TODO item

- PEP-350 code tags, e.g. `# TODO: implement game <due=2025-06-01>`
- Folk code tags, e.g. `# TODO(matth): example.com/ticktet=123 implement game`
- ADVANCED: Add a function decorator, e.g. `@TODO("Work on this")`

While you work
- View the issue-tracker-like single page website `pycodetas issues html`
- Exceptions will be raised or logged when overdue

At build and release time

- Fail build on overdue items (as opposed to failing build on the existence of any code tag, as pylint recommends)
- Generate CHANGELOG.md using the keep-a-changelog format
  - `pycodetags issues changelog`
- Generate DONE.txt, TODO.md, TODO.html files
  - `pycodetags issues todomd`
  - `pycodetags issues donefile`

## Example

```python
from pycodetags_issue_tracker import TODO


# Folk schema
# TODO: Implement payments

# PEP 350 Comment
# TODO: Add a new feature for exporting. <assignee:matth priority=1 2025-06-15>

# Attached to function
@TODO(assignee="matth", due="06/01/2025", comment="Implement payment logic")
def unfinished_feature():
  print("This should not run if overdue and assignee is Matthew.")


@TODO(status="Done", tracker="https://ticketsystem/123")
def finished_feature():
  print("This is a completed feature.")


# Wrapped around any block of code to show what the TODO is referring to
with TODO(comment="Needs Logging, not printing", assignee="carol", due="2025-07-01"):
  print(100 / 3)

if __name__ == "__main__":
  finished_feature()  # won't throw
  unfinished_feature()  # may throw if over due
```

To generate reports:

```text
❯ pycodetags
usage: pycodetags [-h] [--config CONFIG] [--verbose] [--info] [--bug-trail] {data,plugin-info,issues} ...

TODOs in source code as a first class construct, follows PEP350 (v0.3.0)

positional arguments:
  {data,plugin-info,issues}
                        Available commands
    data                Generate code tag reports
    plugin-info         Display information about loaded plugins
    issues              Reports for TODOs and BUGs

options:
  -h, --help            show this help message and exit
  --config CONFIG       Path to config file, defaults to current folder pyproject.toml
  --verbose             verbose level logging output
  --info                info level logging output
  --bug-trail           enable bug trail, local logging

Install pycodetags-issue-tracker plugin for TODO tags.
```

## How it works
Comments with some extra syntax are treated as a data serialization format.

` # DATA: text <default-string default-date default-type data1:value data2:value custom1:value custom2:value`>

Combined with a schema you get a code tag, or a discussion tag, e.g.

`# BUG: Division by zero <MDM 2025-06-06 priority=3 storypoints=5>`

`# QUESTION: Who thought this was a good idea? <MDM 2025-06-06 thread=1 snark=excessive>`

```python
# DATA: text
# text line two
```

- The upper case tag in the `# DATA:` signals the start of a data tag.
- The text continues until a `<>` block terminates or a non-comment line.
- The `<>` block holds space separated key value pairs
  - The key is optional, values are optionally unquoted, single or double-quoted
  - Key value pairs follow, `key=value` or `key:value`
  - default fields are key-less fields identified by their type, e.g. `MDM`, `MDM,JQP`, or `2025-01-01`
  - data fields identified by a schema. PEP-350 is one schema. e.g. `assignee:MDM`, `assignee=MDM`
  - custom fields are data fields that are not expected by the schema. `program-increment:4`

See docs for handling edge cases.

## Basic Workflow

- Write code with TODOs, DONEs, and other code tags.
- Run `pycodetags issues --validate` to ensure data quality is high enough to generate reports.
- Run `pycodetags issues --format <format>` to generate reports.
- Update tags as work is completed.

## Configuration

No workflow or schema is one-size-fits all, so you will almost certainly want to do some configuration.

The expectation is that this config is used at development time, optionally on the build server and *not* when
deployed to production or an end users machine. If you are using only comment code tags, it is not an issue. There
is a runtime cost or risk only when using strongly typed code tags.

See [documentation](https://pycodetags.readthedocs.io/en/latest/) for details.

## Prior Art

PEPs and Standard Library Prior Art

- [PEP 350 - Code Tags](https://peps.python.org/pep-0350/) Rejected proposal, now implemented, mostly by `pycodetags`

## Documentation

- [Readthedocs](https://pycodetags.readthedocs.io/en/latest/)
