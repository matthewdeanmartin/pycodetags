# Usage

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

`# DATA: text <default-string default-date default-type data1:value data2:value custom1:value custom2:value`>

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

