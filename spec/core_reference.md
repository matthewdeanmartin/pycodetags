# Core library reference

Detailed format rules, source editing, and snapshot queries for pycodetags.

## Choose a schema

Choose explicitly in `pyproject.toml`, or pass `schema=` to the library API:

```toml
[tool.pycodetags]
schema = "TDG"
src = ["src"]
```

Use `schema = "PEP350"` for extended PEP-350. Missing or unknown selections raise an actionable error.
`pycodetags init` asks for a schema and
will not choose one for you.

Mixed projects can map different files to different schemas:

```toml
[tool.pycodetags]
schema = "TDG"
src = ["src", "legacy"]

[[tool.pycodetags.schema_paths]]
path = "legacy/*.py"
schema = "PEP350"
```

Paths are relative to the configuration file. Rules use case-sensitive, forward-slash `fnmatch`
patterns (`*` can match slashes). One matching rule overrides the explicitly selected project schema;
multiple matching rules are an error, even if they name the same schema. With only path rules and no
project selection, every file must match a rule. A `schema=` API argument overrides configuration.
Each file has exactly one schema; there is no content-based detection or fallback priority.

## Equivalent records

TDG:

```python
# TODO: Retry failed uploads.
# id=17 issue=100 tracker=https://github.com/acme/uploader/issues/101
# Retry transient failures with exponential backoff.
#
# Stop after five attempts.
```

Extended PEP-350:

```python
# TODO: Retry failed uploads.
# Retry transient failures with exponential backoff.
#
# Stop after five attempts.
# <id=17 issue=100 tracker=https://github.com/acme/uploader/issues/101>
```

In both formats, the text after `TAG:` on the first line is the title. Later comment lines form the
body, excluding metadata. Titles are never wrapped automatically. A title-only tag has an empty body.
Blank comment lines inside the body and body indentation are preserved. TDG ends at a non-comment
line, another recognized tag, or EOF; an empty source line separates ordinary comments from its body.
PEP-350 ends at the closing metadata block, so ordinary comments may follow immediately.

TDG metadata occupies the immediately following line and uses `key=value`. PEP-350 metadata is a
trailing `<...>` block, which may span comment lines; both `key=value` and `key:value` are accepted.
PEP-350 always requires a metadata block, even an empty `<>`. Positional PEP-350 author/date shorthand
is accepted, for example `<alice 2026-09-10>`, and becomes named `author` / `origination_date` properties.

Property values are strings. Quote whitespace, empty values, quotes, and backslashes; serialization
uses JSON-style double-quoted escapes when necessary. Duplicate properties (including aliases) and
malformed metadata are errors. Parsing does not evaluate expressions, supply field defaults, or assign
IDs. `cat` aliases `category`; unknown named properties are retained as custom fields.

A recognized `# TAG:` line begins another record. Put one tag anchor on each comment line. To write a
literal syntax-like body line, prefix its body text with a backslash: `# \TODO: literal text` or
`# \issue=100`. A doubled leading backslash represents a literal backslash. Serializers insert these
escapes when required, including for body lines containing angle brackets. This escape convention is
part of the pycodetags extension, not a claim of upstream TDG compatibility for those escaped lines.
In PEP-350 titles, `\<` represents a literal opening angle bracket and `\\` a literal backslash.

## Python API

```python
from dataclasses import replace
from pycodetags import DATA, dumps, loads, inspect_file

record = loads("# TODO: Retry uploads.\n# issue=100", schema="TDG")
updated = replace(record, title="Retry transient upload failures.", body="Stop after five attempts.")
print(dumps(updated))                    # retains its explicitly selected TDG schema
print(dumps(updated, schema="PEP350"))   # explicit conversion
records = inspect_file("src/upload.py")  # uses explicit project/path configuration
```

Parsed records retain their schema. `title`, `body`, and `tag_id` are the canonical narrative/local-ID
attributes; parsed `comment` mirrors the title for existing readers. Edit `title` when changing a title.
`data_fields` and `custom_fields` hold other properties. `to_flat_dict()` includes the canonical fields
for queries. A newly constructed `DATA` needs `schema=` or explicit project configuration to serialize.

`load`/`load_all` accept source text, `Path` objects, or open streams. `dump`/`dump_all` accept paths or
streams. Caller-owned streams stay open. File output is prepared before the destination is opened.
Custom schema definitions must specify `name`, `format`, `matching_tags`, and the field dictionaries;
copy `TDGSchema` or `PEP350Schema` and customize them. Built-in schema names are reserved.

## Identity and writes

- `id` identifies a tag within a project, independently of title or location changes.
- `issue` identifies its parent issue. Multiple tags may share a parent.
- `tracker` is a ticket URL that multiple independently identified tags may share.

`pycodetags id` explicitly assigns missing local IDs, preserving the configured source format. It
reserves all IDs in the selected files before allocating new ones, rejects duplicates, and refuses to
reset a corrupt counter. Tracker-linked tags also receive local IDs; multiple tags may share the same tracker URL. Keep
`.pycodetags_ids` in version control. Rebuilding a missing counter requires selecting all project sources.

```shell
pycodetags data --format json
pycodetags id --dry-run
pycodetags id --check
pycodetags id
```

Allocation assumes one writer. Reservations are saved before source changes; failures may leave gaps,
which prevents ID reuse. All assignments in one file use a single validated mutation batch.

## Update and delete

```python
from dataclasses import replace
from pycodetags import inspect_file, apply_mutations

records = inspect_file("src/upload.py")
apply_mutations("src/upload.py", [
    (records[0], replace(records[0], title="Retry transient failures.", body="Try five times.")),
    (records[1], None),  # delete
])
```

`update_tags(path, [(old, new), ...])` and `delete_tags(path, [old, ...])` are public convenience
functions. A fresh replacement record inherits the old record's explicitly selected schema unless
it supplies its own. Use `dataclasses.replace` to retain fields you are not changing.
`replace_with_strings` in `pycodetags.mutator` changes titles while retaining bodies and identities.

Every batch validates all source snapshots, spans, overlaps, and rendered comments before writing.
A change anywhere in the source makes file-parsed records stale; reparse after each successful batch
or external edit. File loads fingerprint exact bytes. Parsing caller-supplied text fingerprints logical
text, because the caller may already have normalized line endings; use `inspect_file` or `load(Path)`
when exact byte-level stale detection matters. Whitespace inside tag text is never ignored.

Mutation preserves source encoding (including Python coding declarations and UTF-8 BOM), permission
bits, final-newline state, and bytes outside tag spans. Generated continuation comments retain source
indentation and use the affected line's newline style. Deleting a tag retains the line terminator and
any prefix, including executable code before an inline tag. It may leave a blank line.

Writes use unique temporary files beside the source, flush the prepared bytes, recheck the source,
and replace once. Failed preparations clean up their temporary file. Symlinks and multiply linked
files are rejected. This requires single-writer ownership: the final byte check is not a lock, and an
external writer can still race the replacement. There is no multi-file transaction or crash-durability
guarantee. Source files remain authoritative; the snapshot index can be rebuilt from them.

## Snapshot index and scan exclusions

```toml
[tool.pycodetags]
schema = "TDG"
src = ["src", "tests"]
exclude = ["src/generated", "tests/fixtures/**"]
```

Exclusions match paths relative to the project/configuration root using case-sensitive POSIX patterns.
A directory match prunes traversal; a literal directory name excludes its descendants. There are no
implicit exclusion patterns. Directory symlinks are not followed. These exclusions also apply to core
aggregation and ID assignment. Reserve IDs across all sources you intend to manage together.

```python
from pathlib import Path
from pycodetags import TagIndex, update_tags
from dataclasses import replace

index = TagIndex(Path("."))
work = index.refresh()  # reads current project configuration and source files
records = index.query_snapshot(tag_id="17")
linked = index.query_snapshot(tracker="https://github.com/acme/uploader/issues/101")
in_file = index.query_snapshot(file_path="src/upload.py")

old = records[0]
update_tags(old.file_path, [(old, replace(old, title="Handle transient failures."))])
index.refresh()  # update the snapshot after changing source
```

`TagIndex(root, schema="TDG")` explicitly overrides configured schema selection. Pass `paths=[...]`
and `exclude=[...]` to `refresh` to override configured scan scope. Each refresh describes the entire
selected scope: files removed from that scope are removed from the index. An empty existing directory
is valid; a missing explicit source path fails the refresh.

`query_snapshot` deliberately reads the **last successful snapshot** without checking source files.
Call `refresh` when current-source results are required. There is no watcher or hidden refresh.
Filters combine with AND; duplicate local IDs or tracker URLs return all matching records. Parent
`issue` values are never treated as local IDs. Returned records retain fingerprints, so the mutation
API rejects stale source even when the index has not been refreshed.

Refresh hashes every selected file's bytes, including unchanged files, to detect edits that preserve
size and timestamps. It reparses only files whose contents, selected schema definition, or parser
version changed. Deleted and newly excluded files disappear on a successful refresh. Discovery/read/
parse failures leave the previous snapshot intact. Refresh commits its database changes together,
but is not a simultaneous filesystem snapshot: keep source writers quiescent when that is required.

The database defaults to `.pycodetags.sqlite3` under the supplied root; `database=Path(...)` selects
another location. It is disposable and should be gitignored. Delete it and call `refresh` to rebuild.
Missing, incompatible, corrupt, and foreign databases produce errors rather than empty results or
silently overwritten data. The index contains source text and schema snapshots, so can be substantially
larger than the source comments. It uses standard-library SQLite and JSON, with no new dependency.

`RefreshResult` reports files parsed/unchanged/removed, bytes read, tag count, and timings for discovery,
read/decode/hash, parsing, storage, and the complete refresh. Query indexes accelerate ID/tracker/file
lookups; returning every tag still costs proportionally to the number of results. Full refresh remains
linear in selected source bytes plus discovery, schema checks, and changed-file parsing/storage.
Token extraction has a bounded 32-source process-local cache; persistent parsed records live in SQLite.

See [measured timings and methodology](core_performance.md) and the
[reproducible benchmark](../tests/benchmark_core.py). These are synthetic local measurements, not a
constant-time or repository-wide latency promise.

