# TDG-Style TODO Support

## Background

The [tdg](https://github.com/nicholasgasior/tdg) (TODO Generator) tool uses a multiline comment format that separates a
structured **title** from an optional **key=value property line** from a free-form **body description**. This is
meaningfully superior to plain PEP-350 folk tags for integration with modern issue trackers (GitHub Issues, Jira,
Linear), which distinguish between a short title and a longer description body.

### The TDG syntax

```python
# TODO: This is the title of the issue to create
# category=SomeCategory issue=123 estimate=30m author=alias
# This is a multiline description of the issue
# that will be in the "Body" property of the comment
```

Structural rules (derived from the Go reference parser):

| Line                | Role                                                                                                            |
|---------------------|-----------------------------------------------------------------------------------------------------------------|
| `TODO: <text>`      | **Type + Title** — the first line, colon-separated                                                              |
| `key=value ...`     | **Properties** — optional second line of space-separated `key=value` pairs; no `#` content other than INI pairs |
| Remaining `#` lines | **Body** — free-form description, accumulates until a non-comment line or new TODO anchor                       |

Supported property keys from the Go implementation: `category`, `issue`, `estimate` (accepts `30m` or `2h` → stored as
float hours), `author`.

Supported tag types: `TODO`, `FIXME`, `BUG`, `HACK`.

Boundary detection: A tag ends when either a non-comment line is encountered or a new `TODO:`-style anchor starts.

---

## Why This Matters

PEP-350 folk tags collapse title and description into a single `comment` field. The TDG layout gives us:

- `Title` — used as the issue title in GitHub Issues / Jira / Linear
- `Body` — used as the issue description / body
- Structured properties on a dedicated line, not embedded in angle brackets

The pycodetags `DATA` base class already has a `comment` field but no first-class `title` vs. `body` split. The issue
tracker plugin's `TODO` class likewise has no `body` field. Adding TDG support properly requires both a new parser and a
small data-model extension.

---

## Goals

1. **TDG as a named schema** — a first-class `"TDG"` schema that the core can discover via plugins.
2. **Extended PEP-350 folk tags** — allow TDG-style properties (the `key=value` property line) to be parsed when the
   folk-tag parser is active, without requiring strict TDG format.
3. **Title/body split in the data model** — surface `title` and `body` as distinct fields that the issue-tracker plugin
   can use when creating issues.

---

## Scope

| In scope                               | Out of scope                                                  |
|----------------------------------------|---------------------------------------------------------------|
| Python source files                    | Non-Python languages (Go, JS, etc.) — future work             |
| TDG as a new schema plugin             | Changes to the existing PEP-350 schema                        |
| `estimate` parsing (already in Go ref) | Git blame integration                                         |
| Mapping title/body to GitHub Issues    | Other issue tracker backends (Jira, Linear) in this iteration |

---

## Part 1 — Data Model Changes

### 1.1 `DATA` base class

Add two optional fields to `DATA` in `pycodetags/data_tags/data_tags_classes.py`:

```python
title: str | None = None  # The short issue title (first TODO line)
body: str | None = None  # The long description (lines after the property line)
```

Today `comment` carries everything. After this change:

- For **PEP-350** tags, `comment` continues to mean the inline comment text and `title`/`body` remain `None` (no
  breakage).
- For **TDG** tags, `title` gets the first-line text, `body` gets the accumulated description lines, and `comment` is
  set to `title` for backwards compatibility with any code that reads `comment`.

### 1.2 `TODO` subclass (issue tracker plugin)

In `plugins/pycodetags_issue_tracker/pycodetags_issue_tracker/schema/issue_tracker_classes.py`, promote `title` and
`body` to explicit typed fields (inheriting from `DATA` is enough if the base class already carries them, but explicit
fields make schema introspection easier).

Add to `IssueTrackerSchema` data fields:

```python
"estimate": "float",  # hours, e.g. 0.5 for 30m
"body": "str",
"title": "str",
```

---

## Part 2 — TDG Parser

### 2.1 New module: `folk_tags_tdg_parser.py`

Location: `pycodetags/data_tags/folk_tags_tdg_parser.py`

This module is modelled after `folk_tags_parser.py` but implements the three-zone parse:

```
Zone 1 — anchor line:   # TODO: <title text>
Zone 2 — property line: # key=value key=value ...   (optional, detected heuristically)
Zone 3 — body lines:    # free text...              (zero or more)
```

#### Anchor detection

```python
ANCHOR_RE = re.compile(r"\s*#\s*(TODO|FIXME|BUG|HACK)\s*[:(]\s*(.*)", re.IGNORECASE)
```

#### Property-line detection

A line is a property line if and only if:

1. It starts with `#` (after stripping).
2. It contains no letters outside of `key=value` token shapes — i.e., every token either matches
   `[a-zA-Z_][a-zA-Z0-9_]*=[^\s]+` or is whitespace.
3. It is the **immediate next line** after the anchor (line index + 1).

Heuristic: if splitting on whitespace gives tokens where >50% contain `=`, treat the line as a property line. This
avoids misidentifying a sentence like `# Use the old method=...` as properties.

#### Estimate parsing

Replicate the Go logic: strip trailing `m` → divide by 60; strip trailing `h` → use as-is. Store as `float` in hours in
a `custom_fields["estimate"]` entry. The issue tracker schema will promote this to `data_fields`.

#### Body accumulation

After the (optional) property line, collect all subsequent `# ...` comment lines that do not match a new anchor. Join
with `\n`. Store in `custom_fields["body"]`.

#### Output: `DataTag`

The produced `DataTag` dict looks like:

```python
{
    "code_tag": "TODO",
    "comment": title_text,  # backwards compat
    "fields": {
        "unprocessed_defaults": [],
        "default_fields": {},
        "data_fields": {},
        "custom_fields": {
            "title": title_text,
            "body": body_text,  # may be ""
            "category": "...",  # from property line
            "issue": "123",
            "estimate": "0.5",  # float as string; converter will cast
            "author": "alias",
        },
        "identity_fields": [],
    },
    "original_schema": "TDG",
    ...
}
```

### 2.2 Boundary ambiguity

The main tricky case is knowing when a TDG block ends. Three termination conditions:

1. A non-comment line (same as Go).
2. A new anchor line (`TODO:`, `FIXME:`, etc.) — finalize current, start new.
3. End of comment block (already handled by `find_comment_blocks_from_string`).

The Go parser is single-pass and relies on the fact that a non-comment line ends the block. Python's
`find_comment_blocks_from_string` (via `ast-comments`) already groups contiguous comment lines into a single block,
which means condition 3 is handled for free. The TDG parser only needs to handle condition 2 internally when iterating
lines within a block.

### 2.3 Integration into `data_tags_parsers.py`

In `iterate_comments()`, after the existing folk-tag fallback:

```python
if not found_data_tags and include_folk_tags and schema["matching_tags"]:
# existing folk tag path ...

if not found_data_tags and include_tdg and schema["matching_tags"]:
    found_tdg_tags: list[DataTag] = []
    folk_tags_tdg_parser.process_text(
        final_comment,
        found_tags=found_tdg_tags,
        file_path=str(source_file) if source_file else "",
        valid_tags=schema["matching_tags"],
    )
    things.extend(found_tdg_tags)
```

`include_tdg` would be a new config/CLI flag (default `True` when folk tags are enabled).

Alternatively, TDG parsing can be gated behind a dedicated schema name (`"TDG"`) so it only fires when that schema is
registered — this is the cleaner approach and avoids a flag.

---

## Part 3 — TDG as a Named Schema (Plugin)

Rather than baking TDG into the core, register it as a schema that a plugin can provide. This is consistent with how
`IssueTrackerSchema` works today.

### 3.1 Schema definition

```python
TDGSchema: DataTagSchema = {
    "name": "TDG",
    "matching_tags": ["TODO", "FIXME", "BUG", "HACK"],
    "default_fields": {},
    "data_fields": {
        "title": "str",
        "body": "str",
        "category": "str",
        "issue": "int",
        "estimate": "float",
        "author": "str",
    },
    "data_field_aliases": {
        "cat": "category",
    },
    "field_infos": {},
}
```

The schema can live inside the existing `pycodetags_issue_tracker` plugin (since TDG fields map cleanly onto issue
tracker concepts) or in a new `pycodetags_tdg` plugin if a clean separation is preferred.

### 3.2 Plugin hook

The plugin's `provide_schemas()` returns both `IssueTrackerSchema` and `TDGSchema` (or just `TDGSchema` if separate).
Core will try each registered schema in order.

---

## Part 4 — Extending PEP-350 Folk Tags with TDG Fields

Even without the full TDG schema, users writing folk tags today should be able to add a TDG-style property line and have
`category`, `issue`, `estimate`, `author` extracted.

### 4.1 Changes to `folk_tags_parser.py`

In `process_line()`, after collecting multiline content, check whether **line index + 1** (the line immediately after
the anchor) looks like a TDG property line. If so:

1. Parse it with the same `key=value` logic as the TDG parser.
2. Merge the extracted fields into `found_tag["fields"]["custom_fields"]`.
3. Remove that line from the `content` / body accumulation.

This is opt-in behaviour: it only fires when the next line passes the property-line heuristic, so existing folk tags are
unaffected.

### 4.2 `estimate` field

Add `estimate` to the `IssueTrackerSchema` `data_fields` dict and add the hour/minute parsing logic (already in the Go
reference) to the converter in `converters.py`. The `TODO` dataclass gets a new `estimate: float | None = None` field.

---

## Part 5 — Issue Tracker Plugin: Title + Body in Issues

In `plugins/pycodetags_issue_tracker/`, when creating a GitHub issue:

- **Issue title** ← `todo.title or todo.comment` (prefer explicit title)
- **Issue body** ← `todo.body` (may be empty string or `None`)

This is the key payoff: today the plugin uses `comment` for both, which collapses title and description. After this
change, TDG-format tags produce properly separated title/description in GitHub Issues.

The gh-sync plugin (`pycodetags_issue_tracker_gh_sync`) likely already calls the GitHub Issues API with a `title` and
`body` parameter — confirm and wire in the new fields.

---

## Implementation Order

1. **Data model** — add `title` and `body` to `DATA` and `TODO` (no parser changes yet, fully backwards-compatible).
2. **TDG parser module** — `folk_tags_tdg_parser.py`, unit-tested in isolation.
3. **Parser integration** — wire TDG parser into `iterate_comments()`.
4. **Schema definition** — `TDGSchema` dict, registered via plugin hook.
5. **Folk-tag extension** — property-line detection in `folk_tags_parser.py`.
6. **Estimate field** — add to schema + converter + `TODO` dataclass.
7. **Issue tracker plugin** — use `title`/`body` when creating GitHub issues.

Steps 1–4 are core changes; steps 5–7 are plugin changes. Each step is independently mergeable.

---

## Open Questions

**Q1: Where does TDG schema live?**
Option A: Inside the existing `pycodetags_issue_tracker` plugin — simplest, keeps related schemas together.
Option B: A new `pycodetags_tdg` plugin — clean separation, users can install independently.
Recommendation: Start with Option A; extract to its own plugin only if the schema diverges significantly.

**Q2: `estimate` data type in `DataTagFields`**
`data_fields` today stores `dict[str, Any]` but is treated as `str` in most places. The Go reference converts estimate
to `float64`. We should store it as a string in `custom_fields`/`data_fields` and cast to float only in
`convert_data_to_TODO()` — consistent with how dates are handled.

**Q3: Multiline property line**
The Go parser treats the property line as a single line. Should pycodetags allow the property block to span multiple
lines (e.g., wrapped at 80 chars)? Defer: single-line only for now, matching Go reference behaviour.

**Q4: Conflict with PEP-350 `<field_string>` syntax**
A comment that has both a `<...>` field block and a TDG property line is ambiguous. Resolution: PEP-350 parsing takes
priority (checked first); TDG parser only fires when PEP-350 finds nothing. This already matches the existing folk-tag
fallback pattern.

**Q5: `comment` field backwards compatibility**
If `title` is populated, should `comment` be set to the same value or left `None`? Set to the same value for now so that
any existing code reading `comment` still works. Document that `comment` is deprecated in favour of `title` for
TDG-origin tags.
