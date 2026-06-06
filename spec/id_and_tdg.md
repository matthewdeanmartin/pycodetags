# Data Tag Identity + TDG / GitHub Issue Integration

> Status: **Draft spec, ready for implementation.**
> Supersedes the relevant parts of [`tdg_is_cool_tool.md`](./tdg_is_cool_tool.md) (kept for reference; this
> document is the authoritative plan).
> Author intent captured from design conversation 2026-06-06.

This spec covers the **two most critical missing pieces** of pycodetags:

1. **Identity** — every data tag needs a stable, addressable identity so we can track it across edits, dedupe it,
   and map it to an external issue tracker.
2. **TDG + GitHub Issues** — adopt the [`ribtoks/tdg`](https://github.com/ribtoks/tdg-github-action) comment format
   as a first-class schema, because ~90% of OSS lives on GitHub and the issue tracker is *right there*. The TDG
   `issue=NNN` field is the natural bridge between a code tag and a GitHub issue.

These two problems are deeply linked: **the strongest form of identity a tag can have is a tracker issue number**,
and TDG's `issue=` field is exactly that. So we solve them together.

**Explicitly out of scope for this spec** (next on the roadmap, *not* specced here): the `index` and `update`
commands, the persistent index that makes identity-filling fast, and git-history integration. We design identity so
those are easy to add later, but we do not build them now.

---

## Part 0 — Mental Model: Three Tiers of Identity

The core insight that resolves the author's dilemma ("hash is stable but not across changes; `id=1` needs a central
counter; `id=<guid>` is ugly"): **there is no single identity. There are three tiers, and a tag can have any subset.**

| Tier | Field(s) | Who fills it | Stability | Cost |
|------|----------|--------------|-----------|------|
| **1. Content identity** | *(computed, not stored)* | computed on every parse | Changes when the tag's meaningful text changes | Free |
| **2. Local identity** | `id=N` | a pycodetags tool (`id` command), on demand | Stable forever once assigned | Needs a per-project counter |
| **3. Tracker identity** | `issue=NNN` / `tracker=<url>` | the user, or the gh-sync tool | Stable forever; canonical | Needs network / a tracker |

Rules of the model:

- **Content identity always exists.** It is a hash of the tag's *semantic* fields (see §1.1). Used for dedup,
  "did this tag move/change?", and matching a parsed tag back to a stored one when no stronger id is present.
- **Local identity (`id=N`) is opt-in and tool-assigned.** The user writes tags with no `id`. When a tool that needs
  durable ids runs (e.g. `pycodetags id`), it finds tags lacking an `id`, allocates the next integer from a small
  per-project counter file, and writes `id=N` back into the source comment. This is the author's preferred answer:
  *short, human-readable, tool-managed.*
- **Tracker identity (`issue=NNN`) is the real, canonical id when present.** If a tag has `issue=123`, that GitHub
  issue number *is* its identity for all sync purposes. Local `id` and content hash become secondary.
- **Identity resolution order** (when we need "the id of this tag"): `issue`/`tracker` → `id` → content hash. A tag
  with none of the above still has a content-hash identity and is fully usable; it just can't be durably tracked
  across a rename of its own text until a tool assigns it a stronger id.

This tiering means we **never block** the user. They write plain tags; tools progressively enrich identity only when
a feature needs it.

### Why not the alternatives (recorded so we don't relitigate)

- *Hash of all values as the only id* — rejected: not stable across edits, which is the whole point of an id.
- *`id=<guid>* — rejected: too long, ugly in source, hostile to humans reading the comment.
- *`id=N` with eager central allocation on every write* — rejected: forces centralized "next id" tracking on the
  hot path. **Resolved** by making allocation *lazy and tool-driven*, not write-time.
- *Full-scan to allocate ids* — acknowledged perf problem. **Resolved for now** by scoping the `id` command to
  explicit paths and accepting O(files) cost; the future `index` makes it incremental. We design the counter and the
  command so the index can slot in without changing the on-disk format.

---

## Part 1 — Identity: Data Model & Core Logic

This part is **core** (`pycodetags/`), schema-agnostic, and has **no hard parsing**. Safe for Sonnet.

### 1.1 Content identity (`identity_fields` + hash)

The schema TypedDict already has an unused `identity_fields: list[str]` slot (`data_tags_schema.py`). We give it
meaning: **the ordered list of data-field names whose values define the tag's semantic identity.**

New module: `pycodetags/data_tags/identity.py`

```python
def content_identity(tag: DataTag, schema: DataTagSchema) -> str:
    """Stable short hash of the tag's identity fields.

    - If schema['identity_fields'] is non-empty, hash exactly those data_fields
      (in listed order), plus code_tag and comment.
    - If empty, fall back to hashing (code_tag, comment) only.
    - Normalize whitespace and case-fold nothing (values are case-sensitive).
    - Return first 12 hex chars of sha256 -> e.g. "a1b2c3d4e5f6".
    """
```

- Identity is computed from **values that survive an edit you would consider "the same tag"**. By default this is
  `code_tag` + `comment` (the title). Schemas may add stable fields like `originator` + `origination_date`.
- It explicitly **excludes** volatile/derived fields: `status`, `priority`, `assignee`, `closed_date`, offsets, file
  path. Changing those does *not* change identity.
- Provide `DATA.content_identity(schema)` convenience method mirroring the free function.

`IssueTrackerSchema` gets:
```python
"identity_fields": ["originator", "origination_date"],  # + code_tag + comment implicitly
```
(Discussed but deferred: making `identity_fields` configurable per project. For now it lives in the schema.)

### 1.2 Local identity (`id`)

- Add `id` as a recognized data field. It is an **opaque small integer rendered as a string** (`"1"`, `"42"`).
- It is **never auto-assigned during parsing**. Parsing only *reads* an existing `id`.
- Surface it on `DATA`:
  ```python
  id: str | None = None   # local identity, tool-assigned. NOT a Python builtin shadow concern in dataclass fields,
                          # but expose via property `tag_id` to avoid confusion. (See §1.5.)
  ```
- Add to `IssueTrackerSchema["data_fields"]`: `"id": "int"` (stored/serialized as string per the existing
  date-as-string convention; cast only where needed).

### 1.3 The id counter (per-project)

New module: `pycodetags/identity_counter.py`

- File: `<project_root>/.pycodetags_ids` (sibling to `.pycodetags_cache`; project root = nearest `pyproject.toml`,
  reuse `_get_cache_dir`'s root-finding logic, factored into `find_project_root()`).
- Format: a single JSON object, human-diffable, git-committed (NOT gitignored — ids must be stable across clones):
  ```json
  { "version": 1, "next_id": 43, "allocated": { "42": "a1b2c3d4e5f6" } }
  ```
  - `next_id`: the next integer to hand out.
  - `allocated`: `id -> content_identity` at time of allocation. Lets a future `index` detect collisions / reuse and
    lets us warn if an `id` in source doesn't match the counter.
- API:
  ```python
  class IdCounter:
      @classmethod
      def load(cls, root: Path | None = None) -> "IdCounter": ...
      def allocate(self, content_id: str) -> str:   # returns new id, bumps next_id, records allocation
      def save(self) -> None:                        # atomic write (temp + os.replace, like mutator/cache)
      @property
      def known_ids(self) -> set[str]: ...
  ```
- Concurrency: single-process tool use assumed. Atomic replace on save. No locking in v1 (document the limitation).

### 1.4 Identity resolution helper

In `identity.py`:
```python
def resolve_identity(tag: DATA) -> tuple[str, str]:
    """Return (kind, value) where kind in {"tracker", "id", "content"}.
    Priority: issue/tracker > id > content hash.
    """
```
Used by sync, dedup, and reporting to answer "what is this tag's canonical id right now?".

### 1.5 Naming note (`id` is a Python builtin)

Do **not** name the dataclass field `id` if it causes friction; the **wire/comment field name is `id`** (that is what
appears in source: `id=42`), but the Python attribute should be `tag_id` to avoid shadowing and confusion. The
parser/serializer maps comment-`id` ↔ attribute-`tag_id`. Add `"id"` -> `"tag_id"`? No — keep it simple: the
`data_fields` dict is keyed by the *comment* name `id`; only the strongly-typed `DATA`/`TODO` dataclass uses
`tag_id`. Converters already do this name mapping per-field, so add one line there.

---

## Part 2 — The `id` command (assignment tool)

This is **core orchestration + uses the existing mutator**. No hard parsing. Safe for Sonnet.

New CLI subcommand (core, or in a small plugin — see §6): `pycodetags id [PATHS...]`

Behavior:
1. Collect data tags from the given paths (reuse `aggregate_all_kinds` / `iterate_comments_from_file`).
2. For each tag **lacking** an `id` *and* lacking a tracker `issue` (a tracker-backed tag doesn't need a local id):
   - compute `content_identity`,
   - `IdCounter.allocate(content_id)` → new `id`,
   - build the new `DATA` with `tag_id` set,
   - queue a mutation `(old_tag, new_tag)`.
3. Apply mutations per file via `mutator.apply_mutations` (it already sorts end-to-start to keep offsets valid).
4. `IdCounter.save()`.
5. Print a summary: N tags scanned, M ids assigned, file list.

Flags:
- `--dry-run` — show what would be assigned, write nothing (neither source nor counter).
- `--check` — exit nonzero if any tag is missing an id (for CI / pre-commit). Assigns nothing.
- `--paths` default to config `src` if omitted.

**Perf is explicitly accepted as O(files) for now.** Document in the command help that on large repos this is a full
scan and that an incremental `index` is on the roadmap. Do **not** prematurely optimize.

### 2.1 Round-trip safety (the one real risk)

Assigning an id rewrites the comment via `as_data_comment()`. That serializer must faithfully round-trip an existing
tag plus one new field. Risks:
- Folk tags and TDG tags don't serialize as PEP-350 today.
- `as_data_comment` may reorder/normalize fields.

Mitigation / required tests:
- A round-trip test: parse → assign id → serialize → re-parse, assert all original fields preserved and `id` added.
- For **TDG-origin** tags, prefer writing the id **into the TDG property line** (`id=42`) rather than converting the
  whole comment to PEP-350. This requires a TDG serializer (§4.4). If the TDG serializer is not ready, `id` assignment
  for TDG tags is **deferred** and the command skips them with a warning. PEP-350 tags work from day one.

---

## Part 3 — TDG as a first-class schema

The parser **already exists** (`pycodetags/data_tags/tdg_tags_parser.py`). What's missing is: a registered schema, a
title/body data model, wiring into the collection pipeline, and a serializer. This part is mostly **schema + wiring**
(Sonnet), with **one hard parsing item carved out for Opus** (§4).

### 3.1 Data model: `title` / `body`

Add to `DATA` (`data_tags_classes.py`):
```python
title: str | None = None   # short issue title (the "TODO: <title>" line)
body: str | None = None    # long description (lines after the property line)
```
Rules:
- PEP-350 tags: `title`/`body` stay `None`; `comment` unchanged. **No breakage.**
- TDG tags: `title` = first-line text, `body` = accumulated description, and `comment` is set equal to `title` for
  backward compatibility with any code reading `comment`.

The existing TDG parser already stuffs `body` into `custom_fields["body"]`; promote it to a real field via the schema
(below) and ensure the converter lifts `custom_fields["body"]`/`["title"]` onto the dataclass attributes.

### 3.2 `TDGSchema`

Lives in the issue-tracker plugin (Option A from the old spec — keep related schemas together). New file
`plugins/pycodetags_issue_tracker/pycodetags_issue_tracker/schema/tdg_schema.py`:

```python
TDGSchema: DataTagSchema = {
    "name": "TDG",
    "matching_tags": ["TODO", "FIXME", "BUG", "HACK"],
    "default_fields": {},
    "data_fields": {
        "title": "str",
        "body": "str",
        "category": "str",
        "issue": "int",        # the GitHub issue number — tracker identity
        "estimate": "float",   # hours
        "author": "str",
        "id": "int",           # local identity (shared concept with §1.2)
    },
    "data_field_aliases": {"cat": "category"},
    "field_infos": {},
    "identity_fields": ["issue"],   # issue number is the identity when present; else falls back to content hash
}
```

`provide_schemas()` in the issue-tracker plugin returns `[IssueTrackerSchema, TDGSchema]`.

### 3.3 Wiring TDG into collection

The cleanest gate (the old spec's recommended Option, confirmed here): **TDG fires only when the `TDG` schema is
active**, not behind a separate `include_tdg` flag.

In `data_tags_parsers.iterate_comments`, after PEP-350 and folk-tag passes, add a TDG pass that runs **only for
schemas whose `name == "TDG"`** and only when no stronger tag was already found for that comment block:

```python
for schema in schemas:
    if schema["name"] == "TDG" and not found_data_tags:
        for tdg_tag in tdg_tags_parser.iterate_comments(final_comment, source_file, [schema]):
            # adjust offsets relative to the block, like the folk-tag path does
            things.append(tdg_tag)
```

Ambiguity resolution (locked in):
- **PEP-350 `<...>` field block wins** over TDG when both could match. PEP-350 runs first; TDG only fires when PEP-350
  found nothing in that block (already the existing fallback shape).
- TDG vs folk tag: when `TDG` schema is active, TDG runs **before** the generic folk-tag fallback for that schema.

Activation: user adds `"TDG"` (or `"tdg"`) to `active_schemas` in config. `aggregate_all_kinds` already reads
`config.active_schemas()`; pass the TDG-named schemas through the same as others. (Today only `schema` is passed to
`aggregate_all_kinds`; broaden it to accept the plugin-provided schema list — see §5.)

### 3.4 Converter: lift title/body/estimate/issue/id

In `convert_data_to_TODO` (issue-tracker `converters.py`), add:
```python
title=get_from_custom_or_data("title", tag),
body=get_from_custom_or_data("body", tag),
estimate=get_from_custom_or_data("estimate", tag),   # cast str->float here, like dates
issue=get_from_custom_or_data("issue", tag),
tag_id=get_from_custom_or_data("id", tag),
```
And add the matching fields to the `TODO` dataclass (`issue_tracker_classes.py`):
```python
title: str | None = None
body: str | None = None
estimate: float | None = None
issue: str | None = None
tag_id: str | None = None
```
`estimate` parsing (`30m` → 0.5, `2h` → 2.0) is a small pure function — put it in `converters.py`:
```python
def parse_estimate(raw: str | None) -> float | None: ...   # trailing 'm' -> /60, 'h' -> as-is, bare -> hours
```

---

## Part 4 — THE HARD PARSING ZONE (Opus only)

> Everything in this section touches regex/parsing boundary logic where a wrong heuristic silently corrupts tags.
> **Segregate it.** Do not let Sonnet edit these functions. Each item below is self-contained with its own tests so
> Opus can do them in isolation without the rest of the spec being finished.

### 4.1 Harden the TDG anchor/property/body parser

The existing `tdg_tags_parser.py` regex (`tdg_regex`) is greedy and naive. Required hardening, each with table-driven
unit tests in `tests/test_data_tags/test_tdg_parser.py`:

1. **Property-line detection must be a heuristic, not "always line 2."** Line 2 is a property line **iff** >50% of its
   whitespace tokens match `^[A-Za-z_][A-Za-z0-9_]*=\S+$`. Otherwise line 2 is **body**, and there are zero
   properties. (Prevents `# Use the old method=foo approach` from being parsed as properties.)
2. **Boundary on a new anchor.** Within one comment block, a second `# TODO:`/`# FIXME:`/etc. line **ends** the
   current tag and starts a new one. The current regex's `body_lines` greedily swallows subsequent anchors — fix it.
3. **Body cleaning** must strip exactly one leading `# ` and preserve internal blank comment lines (`#` alone → empty
   body line).
4. **Offsets** must be correct for tag 2..N within a block (the folk parser has a known offset bug; do not inherit it).
5. **Tag-name filtering** against `schema["matching_tags"]` (already present) — keep, add tests for a non-matching
   uppercase word that looks like a tag (`# NOTE:`).

Deliverable: a single function `iterate_comments(source, source_file, schemas) -> Generator[DataTag]` with the same
signature as today, but correct. Keep it pure (no filesystem, no config).

### 4.2 TDG property-line field parser

Reuse `parse_fields` where possible, but the TDG property line uses bare `key=value` space-separated tokens with **no
`<...>` wrapper**. Confirm `parse_fields` handles `=` separators (it does — `[:=]` in the regex). The hard part is
**not** double-promoting `body`/`title` into `unprocessed_defaults`. Add tests.

### 4.3 Folk-tag TDG-property extension (optional, lower priority)

Per the old spec §4: when a folk tag's **immediately following line** passes the property-line heuristic, extract
those fields and remove them from the body. This shares the heuristic from §4.1 — implement the heuristic **once** in
`tdg_tags_parser.py` and import it into `folk_tags_parser.py`. Gate behind the same property-line confidence check so
existing folk tags are untouched. **This is the most error-prone item; do it last and behind tests.**

### 4.4 TDG serializer (`as_tdg_comment`)

Needed for §2.1 (writing `id=` back into a TDG tag without converting it to PEP-350) and for round-trip tests.
```python
def as_tdg_comment(tag: DATA) -> str:
    """
    # TODO: {title}
    # key=value key=value ...        (only non-empty properties; skip title/body)
    # {body line 1}
    # {body line 2}
    """
```
Must round-trip: `parse → as_tdg_comment → parse` is identity on all fields. This is parsing-adjacent (whitespace,
ordering, quoting of values with spaces) → **Opus**.

---

## Part 5 — Pipeline plumbing for multiple active schemas

Currently `aggregate_all_kinds(module, source_path, schema)` takes a **single** schema. To support TDG + IssueTracker
simultaneously we need to thread the plugin-provided schema list through. This is **mechanical, Sonnet-safe**, but
touches several call sites — list them explicitly:

- `aggregate.py`: `aggregate_all_kinds` and `aggregate_all_kinds_multiple_input` accept `schemas: list[DataTagSchema]`
  (keep a single-schema overload/shim for callers that pass one).
- `iterate_comments_from_file` / `iterate_comments` already accept `schemas: list[...]` — good, just pass them through.
- The merge of active schemas: use `list_available_schemas()` (already exists in `common_interfaces.py`) filtered by
  `config.active_schemas()` names. Add a helper `get_active_schemas(config) -> list[DataTagSchema]`.
- Dedup: when multiple schemas match the same comment block, a tag can be produced twice. Add a post-collection dedup
  keyed on `(file_path, offsets, content_identity)`. Put this in `aggregate.py` after collection.

---

## Part 6 — GitHub Issues sync (the payoff)

Wire identity + title/body into `pycodetags_issue_tracker_gh_sync` (currently a 49-line stub that only prints).

Mapping (using TDG/`ribtoks` field names as the contract):

| Code tag field | GitHub issue field |
|----------------|--------------------|
| `title or comment` | issue **title** |
| `body` | issue **body** (append a footer with file:line + content-id) |
| `category` | a **label** |
| `author` | **assignee** (best-effort; map via authors config) |
| `issue=NNN` | the **issue number** to update; if empty, **create** and write the number back |
| `estimate` | appended to body or a label like `estimate:0.5h` |

Sync algorithm (`github-issues-sync` command; keep `--dry-run`):
1. Collect TODO/TDG tags.
2. For each tag, `resolve_identity`:
   - has `issue=NNN` → **update** that GitHub issue (title/body/labels) if changed.
   - no `issue`, has `id`/content-id → **create** a new GitHub issue; on success, **mutate the source** to add
     `issue=<new number>` (via `mutator.apply_mutations`, reusing the TDG serializer from §4.4). This closes the loop:
     a created issue becomes the tag's tracker identity.
   - closed/`status=done` tags → optionally **close** the matching issue.
3. Use the `gh` CLI (already the environment's GitHub tool) or the REST API. Authentication via existing `gh` login.
   **Do not** hardcode tokens.

The body footer (so a human reading the GitHub issue can find the source) and writing `issue=` back are the two
features that make this genuinely useful rather than a one-way dump.

> Network / external-effect caution: creating and updating issues is outward-facing and hard to reverse. The command
> must default to `--dry-run`-style preview unless `--apply` is passed, and must print every create/update/close it is
> about to do. Writing `issue=` back into source is a mutation — gate it behind the same `--apply`.

---

## Phase Plan (dependency-ordered, each independently mergeable)

Legend: **[S]** = Sonnet-safe (schema/wiring/data-model), **[O]** = Opus (hard parsing), **[S+test]** = Sonnet but
needs the round-trip tests to land first.

### Phase 1 — Identity core (no parsing) **[S]**
- `identity.py`: `content_identity`, `resolve_identity`. (§1.1, §1.4)
- `identity_counter.py`: `IdCounter`, `find_project_root` factored out of `cache_utils`. (§1.3)
- `DATA.title`, `DATA.body`, `DATA.tag_id`; `IssueTrackerSchema.identity_fields`. (§1.1, §1.2, §3.1)
- Tests: hashing stability, counter allocate/save/load atomicity.
- **No behavior change to existing parsing.** Fully backward compatible.

### Phase 2 — TDG schema + data model + converter wiring **[S]**
- `TDGSchema`, `provide_schemas` returns it. (§3.2)
- `TODO` gains `title/body/estimate/issue/tag_id`; converter lifts them; `parse_estimate`. (§3.4)
- `get_active_schemas`; thread schema list through `aggregate_all_kinds`. (§5)
- Tests: schema registration, converter lifts fields from `custom_fields`.

### Phase 3 — Hard TDG parser **[O]**  *(can proceed in parallel with Phase 2; only depends on Phase-2 schema shape)*
- Harden `tdg_tags_parser.py` (§4.1, §4.2): property-line heuristic, anchor boundaries, offsets, body cleaning.
- `as_tdg_comment` serializer + round-trip tests (§4.4).
- Wire TDG pass into `iterate_comments` gated on `schema["name"] == "TDG"` (§3.3) — the *wiring* is [S] but lives next
  to the parser, so land it with Phase 3.
- Self-contained test file `tests/test_data_tags/test_tdg_parser.py` (table-driven).

### Phase 4 — `id` command **[S+test]**  *(depends on Phase 1; TDG-id support depends on Phase 3's serializer)*
- `pycodetags id [--dry-run] [--check]` (§2). PEP-350 tags first; TDG tags once §4.4 lands (skip+warn before then).
- Round-trip safety tests (§2.1).
- Post-collection dedup (§5).

### Phase 5 — GitHub Issues sync **[S]**  *(depends on Phases 2–4)*
- Implement `github-issues-sync` for real (§6): title/body/labels/assignee mapping, create→write-back `issue=`,
  update, close. `--apply` gating, dry-run default, body footer.

### Phase 6 — Folk-tag TDG-property extension **[O]**  *(optional, last; highest corruption risk)*
- §4.3. Behind the shared property-line heuristic and a confidence gate. Land only with thorough tests.

---

## Open Questions (with recommended answers)

- **Q: Is `.pycodetags_ids` committed or gitignored?** **Committed.** Ids must be stable across clones and CI.
  (Contrast with `.pycodetags_cache`, which is gitignored.)
- **Q: What if source has `id=42` but the counter doesn't know it (e.g. cloned repo, lost counter)?** On `id`
  command, **reconcile**: any `id` seen in source is recorded into `allocated` and `next_id` is bumped past the max
  seen. The counter is a cache of truth, not the truth; **source is the source of truth.**
- **Q: Collisions — two tags assigned the same `id`?** The `id` command treats source as truth and only *fills blanks*;
  it never reassigns. A future `--check` / `index` can flag duplicate ids as an error.
- **Q: Does identity change when a tag is edited?** Content identity yes; `id` and `issue` no. That's the point — a
  tag with an `id`/`issue` keeps its identity through edits; a bare tag does not until a tool gives it one.
- **Q: Estimate type on the wire?** Stored as the raw string (`30m`) in `data_fields`/`custom_fields`; cast to
  `float` hours only in the converter, consistent with how dates are handled.
- **Q: TDG vs PEP-350 precedence?** PEP-350 wins; TDG is the fallback when PEP-350 finds nothing in a block.

---

## Risk Register

| Risk | Where | Mitigation |
|------|-------|------------|
| Serializer doesn't round-trip → `id` command corrupts source | §2.1, §4.4 | Round-trip tests gate the command; TDG-id deferred until `as_tdg_comment` proven |
| Property-line heuristic misfires → body parsed as fields or vice-versa | §4.1, §4.3 | >50% token rule + dedicated table tests; folk extension behind confidence gate |
| Offset bugs in multi-tag blocks → wrong mutation location | §4.1 | Fix offsets in TDG parser; do not inherit folk parser's known bug; mutator already validates `original_text` before writing |
| Full-scan perf on large repos | §2 | Accepted for now; documented; index on roadmap; counter format index-ready |
| gh-sync creates duplicate issues | §6 | `issue=` write-back closes the loop; `--apply` gating + dry-run default |
| Lost/missing `.pycodetags_ids` | Open Qs | Source is source-of-truth; counter reconciles from source on each run |
