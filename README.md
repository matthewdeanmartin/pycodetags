# pycodetags

You've seen `# TODO:` comments? What if they could be used as an issue tracker?

What if `# TODO:` style comments could serialize and deserialize records, turning comments into a database?

What if you could also write comments as decorators that warn or stop you on the due date?

Replace or complement your `# TODO:` comments with decorators similar to NotImplement, Deprecated or Warning
and get issue tracker features, too.

Lightweight and keeps your issue tracker in your code.

Backwards compatible with both `# TODO:` comments and PEP-350 comments.

## Note on Name

Package name is `pycodetags`. The obvious package name is taken and anything with dash or underscore is ungoogleable. Sorry.

## Installation

For code tags strictly in comments:

`pipx install pycodetags`

For code tag decorators, objects, exceptions, context managers with run-time behavior:

`pip install pycodetags`

Requires python 3.8+. 3.7 will probably work.

The only dependencies are `pluggy` and `ast-comments` and backports of python standard libraries to support old versions
of python. For pure-comment style code tags, pipx install and nothing is installed with your application code.

## Usage

`pycodetags` can work with pre-existing comment based code tags, both the folk-schema style and the PEP-350 style.

Ways to track a TODO item

- PEP-350 code tags, e.g. `# TODO: implement game <due=2025-06-01>`
- Folk code tags, e.g. `# TODO(matth): example.com/ticktet=123 implement game`
- Add a function decorator, e.g. `@TODO("Work on this")`
- Raise an TODOException, e.g. `raise TODOException("Work on this")`
- Add a TODOSkipTest decorator
- Create a python list of TODO() objects.
- You can mix styles.

While you work
- Export reports or view the issue-tracker-like single page website
- Exceptions will be raised or logs emitted depending on due dates and the current responsible user

At build time

- Fail build on overdue items (as opposed to failing build on the existence of any code tag, as pylint recommends)
- Generate DONE.txt, TODO.md, TODO.html files

At release time

- Generate CHANGELOG.md using the keep-a-changelog format

## Example

```python
from pycodetags import TODO


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
❯ code_tags --help
usage: code_tags [-h] {report,plugin-info} ...

TODOs in source code as a first class construct (v0.1.0)

positional arguments:
  {report,plugin-info}
                        Available commands
    report              Generate code tag reports
    plugin-info         Display information about loaded plugins
 
options:
  -h, --help            show this help message and exit
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
- Run `pycodetags report --validate` to ensure data quality is high enough to generate reports.
- Run `pycodetags report` to generate reports.
- Update tags as work is completed.

## Configuration

No workflow or schema is one-size-fits all, so you will almost certainly want to do some configuration.

The expectation is that this config is used at development time, optionally on the build server and *not* when
deployed to production or an end users machine. If you are using only comment code tags, it is not an issue. There
is a runtime cost or risk only when using strongly typed code tags.

```toml
[tool.code_tags]
# Range Validation, Range Sources
# Empty list means use file
valid_authors = []
valid_authors_file = "AUTHORS.md"
# Can be Gnits, single_column, humans.txt
valid_authors_schema = "single_column"
# Case-insensitive. Needs at least "done"
valid_status = [
    "planning",
    "ready",
    "done",
    "development",
    "inprogress",
    "testing",
    "closed",
    "fixed",
    "nobug",
    "wontfix"
]
# Only displayed
valid_categories = []
# Only displayed
valid_priorities = ["high", "medium", "low"]

# Used to support change log generation and other features.
closed_status = ["done", "closed", "fixed", "nobug", "wontfix"]
# Empty list means no restrictions
valid_releases = []
# Use to look up valid releases (versions numbers)
valid_releases_file = "CHANGELOG.md"
valid_releases_file_schema = "CHANGELOG.md"
# Used in sorting and views
releases_schema = "semantic"
# Subsection of release. Only displayed.
valid_iterations = ["1", "2", "3", "4"]

# Empty list means all are allowed
valid_custom_field_names = []
# Originator and origination date are important for issue identification
# Without it, heuristics are more likely to fail to match issues to their counterpart in git history
mandatory_fields = ["originator", "origination_date"]
# Helpful for parsing tracker field, used to make ticket a clickable url
tracker_domain = "example.com"
# Can be url or ticket
tracker_style = "url"

# Active user from "os", "env", "git"
user_identification_technique = "os"
# .env variable if method is "env"
user_env_var = "CODE_TAGS_USER"

# Defines the action for a TODO condition: "stop", "warn", "nothing".
enable_actions = true
default_action = "warn"
action_on_past_due = true
action_only_on_responsible_user = true

# Environment detection
disable_on_ci = true

# Use .env file
use_dot_env = true

# default CLI arguments
modules = ["demo","code_tags"]
src = ["demo", "code_tags", "tests", "plugins"]
active_schemas = ["todo", "folk"]
```

## Prior Art

PEPs and Standard Library Prior Art

- [PEP 350 - Code Tags](https://peps.python.org/pep-0350/) Rejected proposal
- [NotImplementedException](https://docs.python.org/3/library/exceptions.html#NotImplementedError) is a blunt way to stop code at an undone point
- `pass` does the same, but doesn't care if you haven't gotten around to it. Linters might make you get
  rid of pass if you've added a docstring, making pass syntactically unnecessary.
- print/logging/warning is noiser way to show undone tasks.
- [DeprecationWarning](https://docs.python.org/3/library/exceptions.html#DeprecationWarning) Deprecation shows a future code removal task.

Community Python Tools

- [todo](https://pypi.org/project/todo/) Extract and print TODOs in code base
- [geoffrey-todo](https://pypi.org/project/geoffrey-todo/) Same.
- [flake8-todo](https://pypi.org/project/flake8-todo/) Yell at you if you leave TODO in the source. Pylint also does this.
- pytest's skip test is a type of TODO
- [xfail](https://pypi.org/project/xfail/) - Same, but as a plugin
- [deprecation](https://pypi.org/project/deprecation/) Deprecation attribute

See [PRIOR_ART.md](docs/PRIOR_ART.md) for survey of the whole ecosystem.

## Documentation

- [User Manual](docs/USER_MANUAL.md)
- [Data Model](docs/DATA_MODEL.md)
- [Design](docs/DESIGN.md)
- [FAQ](docs/FAQ.md)
