# Data Model

A folk schema is a schema that the community follows without a defined standards and has many, many idiosyncratic
examples in the wild.

## Folk schema

- tag - upper case or well known word followed by `:`. Could be anything, usually uppercase.
- default_field - values in parentheses (value1, value2). Folk variations on separator, both comma and whitespace.
- custom_fields - named fields in parentheses, e.g (field1=value1, field2=value2). Folk variation on syntax.
- comment - free text
- tracker - first url in message. No way in advance to recognize an issue number.
- file_path - Internal field, only has meaning while tool is running on one machine
- line_number - mutable field.

## PEP 350 Schema

- code tag. Identity field. Upper case, many aliases.
- comment.
- fields - mixture of expected and unexpected fields
  - **custom_fields** - name fields in angle brackets. Soft required even if empty, e.g. `<>`. Mutable. Idiosyncratic.
  - **priority**. Mutable. Idiosyncratic.
  - **due**. Should be a point in time, not a time span. Accept anything, redisplay as YYYY-MM-DD. Mutable.
  - **tracker**. Identity field, but many TODOs could have the same tracker id/url. A URL or issue tracker ID. Mutable.
  - **release**. Means completed release! Means same as version. Mutable. Idiosyncratic. Can validate to a user defined list or Changelog file.
  - **iteration**. Mutable. Idiosyncratic. Can validate to a user defined list.
  - **status**. Needs at least a synonym for "done". Everything else is idiosyncratic. Mutable. Can validate to a user defined list.
  - **category**. Mutable. Idiosyncratic. Can validate to a user defined list.
  - **assignee**. Mutable. Can validate to a user defined list or Authors file.
  - **originator**. Identity field, when available. Immutable. Can validate to a user defined list or Authors file.

**Note on custom fields:** If fields match an objects parent fields and the parent field is empty, it will be promoted. If
a parent field already exists with a value, a warning will be logged and the parent field will not be overwritten. If
there is a name clash with a pycodetags internal field, a warnning will be logged.

Expected fields can be expected to follow PEP350. Other fields are a folk schema.

## Strongly Typed Code Tags

- **folk-schema fields**

  - code_tag - e.g. TODO, HACK, BUG, etc.
  - comment - unstructured text

- **people fields**

  - assignee - Who should do the work - PEP350
  - originator - Who wants the work to be done - PEP350

- **due fields**

  - origination_date, PEP350 mentions origination_date (parallel naming to originator)
  - due- PEP350
  - release - means same as version. PEP350 (ALIAS?!)
  - release_due - Missing from PEP350
  - iteration - PEP350 team idiosyncratic category
  - release_due (ALIAS?!)

- **done fields**

  - change_type # e.g. Added, Changed, Deprecated, Removed, Fixed, Security
  - closed_date
  - done_comment - # Implied PEP350 standard for DONE.txt file

- **integration fields**

  - tracker - Can be just a ticket number or a url

- **custom workflow fields**

  - priority - team idiosyncratic category
  - status - team idiosyncratic category
  - category - team idiosyncratic category

- **Source Mapping**

  - file_name
  - line_number

- **Schema Fields**

  - original_text
  - original_schema
  - default_field_meaning - Which field a default field represents. Only meaningful for folk schema tags.
