# Design

This application is broadly inspired by javadoc/docstring code tags, IDE TODO trackers and PEP-350.

There isn't a strict standard, so the code-tags needs to make some decisions.

No workflow tool can work for all possible workflows.

## Out of scope of data tags, possibley good candidates for plugins

- all docstring parsing, including `@TODO` and other extensions of the docstring standards. Parsing 3 docstring standards is too much scope.
- pure documentation, other than markers to indicate where documentation is needed
- code review workflows. This could be a crazy but good idea for a new library or tool.
- discussion, e.g. `# QUESTION:`/`# REPLY`. This could be a crazy but good idea for a new library or tool.
- multi-programming-language support. The goal is to support localization on day one.
- integrations that strongly favor one issue tracker. The goal is to provide pytest-like plugin options.


## Supported Item types

Items can be in comments or in strongly typed code. Strongly typed code enforces structure, required fields,
etc, but also can exhibit behaviors, such as stopping, logging or conditionally stopping.

Strongly typed code tag items can be:

- TODO object or decorator
- Aliased TODO tags are idiosyncratic to a given team.
- Specialized Exception
- Specialized Skip-Test decorator

Comment Tags can be

- Folk-schema
- PEP-350 schema

The PEP-350 schema is an approximation because it never matured to an actual standard and as far as I know, no
other implementations.

## Differences from folk Schema

Folk schema code tags are of the form:

`[comment symbols] [mnemonic]([users]): [comment text]`

`[comment symbols] [mnemonic](field=value field=value): [comment text]`

- The comment symbols depend on the programming language and could be single line or multiline style.
- The code tag may be a section of javadoc or docstring. This library will not attempt to deal with those kind of code
  tags because they are part of a much more complex schema that varies greatly by language.
- The menumonics can vary, but are usually upper case, and can have many synonyms.
- The user is often omitted or in parentheses. Users can be separated by commas.
- An optional colon separates the mnemonic.
- The comment text might span multiple lines. This is ambiguous and as far as I can tell there is no universal rule that
  will capture the users intent.

### Disadvantages

The folk schema is limited to about three standard fields. The comment texts end can't be determined.

At best, additional fields could be derived using an AI.

### Advantages

Many tools exist for the extraction of folk code tags to reports.

The pattern can be applied to multiple programming languages

Linters let you enforce a policy of never letting developer use code tags. This seems counter-productive, except for
the narrow workflow where a TODO is added for very brief period of time before commiting to source control.

## Differences from PEP-350

See [PEP-350](https://peps.python.org/pep-0350/). The PEP was rejected and I'm not going to consider the final state
to be something anyone should stick to.

PEP-350 moves the fields to a key-value pair data structure inside angle brackets, otherwise it is roughly the same
as the folk-schema.

Roughly...
```
(?P<mnemonic>[A-Z\?\!]{3,}) # An all-caps mnemonic (e.g., FIXME, BUG, ???)
\s*:\s* # A colon with optional whitespace
(?P<comment>.*?)            # The comment text (non-greedy)
<                           # The start of the field block
(?P<field_string>.*)        # The content of the fields
>                           # The end of the field block
```



### Advantages

Allows for attaching fields in a machine parsable way.

Standard has many suggestions for tooling.

### Disadvantages

While it allows for default fields that don't require typing a field name, it requires the user to recognize fields
by location.

The field abbreviations are cryptic and some mnemonics are obscure.

### Changes that the `code_tag` library will make

- The name "code tag" will have a space and will not be written as "codetag"
- `???` and `!!!` are not valid mnemonics
- Code tags can be on same line as code, following source code.
- A final `<>` is optional to indicate the end.
- End is inferred by next blank or non comment line.
- Not valid if in a multiple line string, `"""`
- Dates as weeks will not be support.
- Meaning of person (default field) will not be inferred by context and is always `assignee`. Originator must be specified explicitly.
- **TBD**: Assignee is either a union of list/str or Assignees is always plural and is always list or something else
- No parsing of person, i.e. we won't attempt to detect initials, John Doe != JD
- Date format is not `YYYY[-MM[-DD]]` but is `YYYY-MM-DD`. Optional month and day complicate any code using a date. 
- Priority has no expected range, use model pep350.toml config to simulate standard.
- tracker, release, iteration are alphanumeric, not numeric

## Strongly Typed Code Tags

### Object lists

An object list is a global variable with TODOs.

```python
from pycodetags import TODO

TODOs = [TODO("Add accept payment feature")]
```

```python
from pycodetags import TODO


@TODO("Add accept payment feature")
def store_front():
    pass
```

```python
from pycodetags import TodoException


def store_front():
    raise TodoException("Add accept payment feature")
```

```python
from pycodetags import TodoFixTest


@TodoFixTest("Something dodgy about this constant assertion")
def test_():
    assert 1 / 0
```

### Advantages

- Can validate fields at runtime
- Field are strongly typed
- Can stop or conditionally stop at runtime
- Can log at runtime
- Can use purely as a metadata for tooling
- Can export to variety of formats

### Disadvantages

- Tiny runtime cost
- Will not be easy to do a two-way sync with any external tracker
- If done items are deleted, they're not tracked, except in git history. If they aren't deleted, they will clutter the code.

## Workflows supported

Due Dates

- Calendar driven. You might have contractual obligations to complete something by some time.
- Version driven. This is a side project or open source project. Work happens as time is available.

Team work

- Assigned tasks. Unfinished items are assigned to someone.
- Credit-only. At time of completion, the author can take credit for the change.

## Integrations

- Issue tracker URL/Number
- Source Control
- (Near) Standard file formats
  - AUTHORS
  - CHANGELOG (keep-a-changelog)

## Output files

- Keep-a-change-log (based on popular website and existing tools)
- DONE file, Markdown. (mentioned by PEP 350)
- TODO file, Markdown. (some standards proposals based on gitlab checkboxs)
- Calendar, iCal
- JSON for arbitrary integrations
- HTML
  - Simple, single HTML file
  - Website with filtering, search, detail page and dashboards

## Extension patterns

Workflows are very idiosyncratic.

Dimensions of idiosyncrasy

- single person vs team. Assignee and originator don't matter in single person projects.
- open source vs commercial. Deadlines are arbitrary or version/release based in opensource.
- scrum vs kanban style. Scrum gives groups things by deadlines. Kanban assumes everything is due now and items are worked as they flow in.
- isolated vs integrated with pre-existing tools, especially Jira and the like.
- Naming. Every person and team could prefer to name things differently.

Supported Extension points

- Valid ranges of each field via config file
- Extracting users from AUTHORs or config file
- Extracting version from CHANGELOG in keepachangelog format
