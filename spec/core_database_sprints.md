# Core library: four sprints

This plan supersedes conflicting design decisions in `id_and_tdg.md`. There are no migration or
backward-compatibility requirements for the old tag behavior. Work stays in the core library and its
tests; plugin implementation is outside this plan. Stop after each sprint for discussion with the owner.

## Agreed contract

- Develop locally on Python 3.14; support Python 3.9 through 3.15. Verify the full interpreter matrix.
- Require an explicit schema, supplied through project configuration or the library API. Never infer a
  project's schema, and never silently choose TDG or PEP-350. Missing configuration is an actionable error.
- Make TDG a built-in schema and support extended PEP-350 as an alternative.
- In both formats, text after `TAG:` on the first line is the title; subsequent comment lines are the
  body. TDG properties follow the title; PEP-350 metadata is a trailing `<...>` block. Metadata is not
  title/body text. Preserve blank lines within the body. A one-line tag has an empty body. Never wrap
  a title into body text automatically.
- `id` identifies a tag within a project. `issue` denotes a parent issue and is never a unique tag key.
  `tracker` links to the issue representing this particular tag, using a full issue URL.
- Parsing never allocates IDs. Allocation is an explicit operation. Source files remain authoritative.
- Replace tests that encode rejected behavior with tests of the agreed contract. Keep useful existing
  coverage. Add concise Keep a Changelog entries under `[Unreleased]` for delivered changes only.

## Sprint 1: source addressing, identity, and Python support

Deliver:
- Align package metadata, local tooling, documentation, and CI with Python 3.9–3.15 / local 3.14.
- Locate comments by real source positions, including repeated text, nested code, Unicode, and inline
  comments. Ensure TDG source spans address the exact tag text, including indented single-line tags.
- Separate parent issues from tracker identity. Reserve all IDs found in the selected files before
  allocating any new ones; reject duplicate source IDs and unreadable/corrupt counters before writing.
- Deduplicate repeated input paths and preserve observed IDs in the counter even when no IDs are added.

Acceptance:
- Repeated comments at different positions remain separate and can be addressed individually.
- Parent-only tags receive local IDs; linked tracker URLs still resolve as tracker identities.
- Allocation cannot reuse an ID found later in the selected input. Duplicate IDs fail without writes.
- Dry-run/check leave source and counter unchanged. A corrupt counter cannot silently restart at one.
- Formatting/linting and the supported interpreter test matrix pass, or environmental blocks are
  explicitly recorded. Record available 3.15 prerelease version when applicable.

Scope boundary: explicit schema configuration and title/body parsing land in Sprint 2. Mutation
transaction hardening lands in Sprint 3. Fixing source positions may also eliminate measured quadratic
work; indexing and repository-level performance remain Sprint 4.

## Sprint 2: explicit schemas and equivalent tag formats

Deliver built-in TDG and extended PEP-350 schemas, explicit configuration/API selection, coherent
title/body/identity fields, and serializers used consistently by public APIs. Remove fallback schema
guessing. Specify how explicitly configured multiple schemas apply to source paths without ambiguity.

Acceptance: unconfigured calls fail clearly; both formats represent equivalent records; quoted
properties, multiline metadata, blank body lines, and multiple tags round-trip; a tag is collected once;
public load/dump operations preserve the selected format and semantic fields. No implicit ID creation.

## Sprint 3: safe updates and deletes

Deliver a public update/delete path backed by one validated mutation batch per file, regardless of
format. Reject overlapping/invalid spans and stale source; preserve encoding/newlines, indentation,
and unrelated source text. Use unique temporary files and document the concurrency boundary.

Acceptance: updates and deletes work for both schemas and multiple tags in one file; failed validation
does not change source; mixed-format batches do not invalidate their own offsets; surrounding code and
body formatting survive. Do not claim multi-file transactions or concurrent-writer safety unless built
and tested explicitly. Retain the reservation-before-source-write ordering delivered in Sprint 1.

## Sprint 4: measured performance and a rebuildable index

Benchmark uncached scans, warm scans, ID lookup, batch writes, and one-file changes on representative
repository shapes. Remove repeated whole-file operations and support explicit scan exclusions.
Implement a disposable SQLite index for tag/file/tracker lookup with source files authoritative.

Initial design assumption: explicit refresh, no background watcher. Record file fingerprints and
parser/schema configuration versions; refresh changed files, remove deleted-file entries, and validate
source before mutations. Confirm the query freshness policy at the Sprint 3 checkpoint.

Acceptance: indexed and fresh-scan results agree; edits/deletions/config changes invalidate correctly;
index removal is recoverable; measured timings distinguish discovery, parsing, and query costs. Document
consistency and complexity without promising constant-time full repository refreshes.

## Progress

- Sprints 1–3: complete; owner approved continuing at each checkpoint.
- Sprint 4: complete (2026-09-10); all four sprints delivered.

### Sprint 1 results

Implemented tokenizer-based source addressing, exact TDG spans, separate parent/tracker identity,
two-pass ID reservation, duplicate-ID rejection, counter validation, and reservation persistence before
source writes. Removed the unused `ast-comments` dependency. Updated Python support metadata, tox,
CI, documentation, and the lockfile. The local environment uses Python 3.14.6.

Validation: 371 passed / 6 skipped on each of Python 3.9.13, 3.10.11, 3.11.9, 3.12.10, 3.13.13,
3.14.6, and 3.15.0rc2. Coverage exceeds the 65% requirement on every version. Black, isort,
pre-commit, KACL-M `validate --all`, and `uv pip check` passed.

The first matrix run selected an old 3.15.0a8 installation whose coverage extension failed to load.
The supported 3.15 check was rerun successfully against the installed release candidate:

```powershell
$python315Path = uv python find 3.15
tox run -e py315 --discover $python315Path
```

An exploratory uncached extraction benchmark on local Python 3.14.6 measured medians of 0.0052s,
0.0075s, and 0.0175s for 1,000, 2,000, and 4,000 tags respectively. Each synthetic tag occupies its own
comment line followed by an assignment; three repetitions bypassed the extraction cache. These are
extraction timings, not repository scan/query timings. The earlier baseline used Python 3.13, so no
precise cross-version speedup ratio is claimed.

Remaining boundaries: schema selection/title-body equivalence are still Sprint 2; safe mixed-format
mutation batches and broader file preservation are Sprint 3; indexing is Sprint 4. Allocation assumes
one writer. Rebuilding a missing counter requires selecting all project source paths. Persisted
reservations can leave unused IDs after a failed write, intentionally preventing reuse.


### Sprint 2 results

Implemented built-in TDG and extended PEP-350 schemas with mandatory explicit selection through
configuration or the API. Per-path rules select exactly one schema per file; overlapping rules fail.
Parsed records retain the selected schema. Shared parsing/serialization preserves canonical titles,
bodies, local IDs, named properties, quoted values, multiline PEP metadata, and blank body lines.
Literal syntax-like narrative text uses documented escapes. No parsing operation allocates IDs.

Public load/dump operations use the shared format implementation and keep caller-owned streams open.
CLI initialization requires a schema choice; CLI source paths and counters resolve against the selected
configuration file. Replaced obsolete tests and updated README and concise Unreleased changelog entries.

Sprint 3 remains responsible for mutation validation, stale-source protection, and file preservation.
Sprint 4 remains responsible for indexing and repository performance measurements. Plugin implementations
were not changed; their existing non-Python source discovery hook remains available.

Validation: 393 passed / 5 skipped on every interpreter from Python 3.9 through 3.15 (3.15.0rc2,
selected with tox --discover). Coverage is 84.62%, above the 65% requirement. Black, isort, pre-commit,
KACL-M validate --all, dependency compatibility, and git diff whitespace checks pass. The local
Python 3.14 environment and lockfile are synchronized. Existing Hypothesis collection and virtualenv
cache-location warnings do not prevent any matrix environment from passing.


### Sprint 3 implementation contract

The owner confirmed TDG ends at the end of its contiguous comment block and PEP-350 ends at the
closing metadata block. Keep those boundaries unchanged. Mutations validate a complete batch before
writing: source provenance, exact logical text, bounded non-overlapping spans, and serialization.
File parses carry a byte fingerprint; text parses carry a logical-text fingerprint (line endings may
already have been normalized by the caller). Preserve source encoding/BOM, surrounding bytes, existing
line endings, indentation, file mode, and final-newline state. New replacement lines use the affected
line's newline style. A fresh replacement without a schema inherits the old record's explicit schema.

Use a unique temporary file beside the source, flush it, recheck source bytes, and replace once.
This is one-file replacement with single-writer ownership, not a lock or multi-file transaction.
Keep ID reservations persisted before any source writes. Export update/delete batch helpers publicly.


### Sprint 3 results

Implemented public update_tags/delete_tags/apply_mutations with one validated replacement per file.
Validation checks source fingerprints, file identity, exact logical tag text, coordinate bounds, and
span overlap. File loads retain byte fingerprints; caller-supplied text retains logical-text fingerprints.
Rendering inherits the old explicit schema for fresh replacement records. Title-only edits retain body,
properties, and identity. ID assignment now uses one batch per file and preserves reservation ordering.

Added Python encoding-aware source reads and byte-preserving writes. Tested UTF-8, UTF-8 BOM, Latin-1,
LF/CRLF/CR, mixed line endings, indentation, inline executable prefixes, blank body lines, and EOF without
a newline. Unique temporary files are flushed and cleaned on failures; final source bytes are rechecked
before replacement. Symlinks and hardlinked files are rejected. No concurrent-writer or multi-file
transaction guarantee is claimed. Reparse after a successful mutation before another batch.

Batch reconstruction computes line starts once and assembles disjoint replacements in one pass after
sorting, avoiding repeated whole-file splitting per tag. Repository benchmarks and indexing remain
Sprint 4. Index freshness policy still needs to be settled before its query API is implemented.


Validation: 440 passed / 5 skipped on each of Python 3.9.13, 3.10.11, 3.11.9, 3.12.10, 3.13.13,
3.14.6, and 3.15.0rc2. Coverage is approximately 85.4%, above the required 65%. The first matrix
exposed older tokenize behavior for Latin-1 with CR-only line endings; normalizing only the encoding
probe fixed it, and the complete matrix passed on the final code. Black, isort, pre-commit, KACL-M
validate --all, dependency compatibility, and whitespace checks pass.


### Sprint 4 implementation contract

Use explicit refresh and explicitly named query_snapshot operations. Snapshot queries never silently
scan or claim current filesystem freshness. Refresh reads configuration anew, discovers selected Python
files with explicit exclusions, hashes file bytes, reparses changed files/schema definitions/parser
versions, and removes deleted or newly excluded files in one SQLite transaction. Read every selected
file to detect content changes even if size and timestamps were preserved; warm refresh remains linear
in source bytes. No background watcher. The index is disposable; source files remain authoritative.

Index results retain source fingerprints and use Sprint 3 mutation validation. Query by local ID,
tracker URL, or file path using SQLite indexes. A missing/incompatible index requires refresh; arbitrary
or corrupt databases are not silently overwritten. Record discovery, read/hash, parsing, storage, and
lookup timings on many-small-file and few-large-file fixtures. Measure batch writes and one-file edits.


### Sprint 4 results

Implemented TagIndex with explicit refresh/query_snapshot APIs, SQLite ID/tracker/file indexes,
byte fingerprints, schema-definition/parser-version invalidation, deleted/excluded-file removal,
and transactional refresh rollback. Indexed records retain Sprint 3 mutation provenance. Missing or
incompatible indexes require refresh/rebuild; foreign databases are not overwritten. No watcher or
implicit freshness claim. Duplicate local IDs return all matches, allowing callers to diagnose them.

Added shared source discovery with explicit directory pruning for indexing, aggregation, and ID
assignment. Overlapping aggregate inputs no longer reparse the same file. Token extraction uses a
bounded process-local cache; persistent parsed records are stored as JSON in SQLite. Tokenization
failures now fail a scan explicitly rather than masquerading as an empty file. Refresh resolves each
selected schema definition once per run and hashes every selected file, even on warm refresh.

Benchmarks and methodology are recorded in core_performance.md with raw core_performance.json and
an executable benchmark in tests/benchmark_core.py. For 3,000 tags, fresh scans measured approximately
352–401 ms, indexed ID lookups about 0.6 ms, warm refreshes 7–64 ms, and one-file refreshes 67–151 ms.
These are local synthetic measurements; the report documents cache state, output sizes, storage
footprint, phase timings, and consistency/complexity limits.


Validation: 463 passed / 5 skipped on each of Python 3.9.13, 3.10.11, 3.11.9, 3.12.10, 3.13.13,
3.14.6, and 3.15.0rc2. Coverage is 85.92%, above the required 65%. Black, isort, pre-commit,
KACL-M validate --all, dependency compatibility, and whitespace checks pass. Test-only SQLite
connection cleanup was corrected after the matrix; all 23 index tests were then rerun successfully
on Python 3.13 with ResourceWarning treated as an error. Existing Hypothesis collection and
virtualenv cache-location warnings remain non-blocking.

All four sprints are complete. Changes remain uncommitted for owner review; no release was published.
