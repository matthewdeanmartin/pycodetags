"""
The ``pycodetags id`` command: lazily assign stable local ids (``id=N``) to data tags.

This is the *tool-driven* half of the identity model (see ``spec/id_and_tdg.md`` Part 2). The user
writes plain tags with no ``id``. When durable identity is needed, this command:

1. scans the given paths for data tags,
2. skips any tag that already has an ``id`` *or* a tracker ``issue`` (a tracker-backed tag already has
   the strongest identity and does not need a local one),
3. allocates the next integer from the per-project counter (``.pycodetags_ids``),
4. rewrites the source comment to add ``id=N`` -- in PEP-350 form for PEP-350 tags and in TDG form for
   TDG-origin tags, so neither is mangled into the other's syntax,
5. saves the counter.

Performance is intentionally O(files): on a large repo this is a full scan. An incremental ``index``
is on the roadmap; the counter file format is already index-ready. Do not prematurely optimize here.

This module is core: it works for PEP-350 tags with no plugins installed. TDG-id support activates only
when the ``TDG`` schema is active (the issue-tracker plugin provides it) and uses the proven
``as_tdg_comment`` serializer.
"""

from __future__ import annotations

import dataclasses
import logging
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from pycodetags import mutator
from pycodetags.aggregate import dedup_data_objects
from pycodetags.app_config import get_code_tags_config
from pycodetags.common_interfaces import get_active_schemas, list_available_schemas
from pycodetags.data_tags import (
    DATA,
    DataTagSchema,
    convert_data_tag_to_data_object,
    iterate_comments_from_file,
    tdg_tags_parser,
)
from pycodetags.data_tags.identity import content_identity_for_data, resolve_identity
from pycodetags.identity_counter import IdCounter
from pycodetags.pure_data_schema import PureDataSchema

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class IdRunResult:
    """Summary of an ``id`` command run, returned for testing and reporting."""

    scanned: int = 0
    assigned: int = 0
    skipped_have_id: int = 0
    skipped_have_issue: int = 0
    skipped_unsupported: int = 0
    skipped_shared_block: int = 0
    files_changed: list[str] = dataclasses.field(default_factory=list)
    # tag content-id -> newly assigned id, in assignment order (for --dry-run reporting and tests).
    assignments: list[tuple[str, str]] = dataclasses.field(default_factory=list)


def _schema_for_tag(tag: DATA, schemas_by_name: dict[str, DataTagSchema]) -> DataTagSchema:
    """Pick the schema that governs a tag's identity, keyed off ``original_schema``.

    TDG-origin tags resolve to the ``TDG`` schema (whose ``identity_fields`` is ``["issue"]``); every
    other tag falls back to the primary schema, which for ``id`` purposes is ``PureDataSchema`` (no
    extra identity fields, so identity is ``code_tag`` + ``comment``).
    """
    origin = (tag.original_schema or "").upper()
    if origin == "TDG" and "TDG" in schemas_by_name:
        return schemas_by_name["TDG"]
    return schemas_by_name.get("PUREDATA", PureDataSchema)


def _tdg_serializer(tag: DATA) -> str:
    """Serialize a TDG-origin tag back to TDG comment form, including its ``id`` property."""
    properties: dict[str, object] = {}
    for field_set in (tag.data_fields, tag.custom_fields):
        if field_set:
            properties.update(field_set)
    if tag.tag_id is not None:
        properties["id"] = tag.tag_id
    return tdg_tags_parser.as_tdg_comment(
        code_tag=tag.code_tag or "TODO",
        title=tag.title if tag.title is not None else tag.comment,
        body=tag.body,
        properties=properties,
    )


def _with_id(tag: DATA, new_id: str) -> DATA:
    """Return a copy of ``tag`` carrying ``id=new_id`` in both the attribute and the field dicts.

    PEP-350 serialization (``as_data_comment``) reads ``id`` out of ``data_fields``/``custom_fields``,
    not the ``tag_id`` attribute, so we must write it there too; the TDG serializer reads ``tag_id``.
    Writing both keeps every serializer happy.
    """
    new_tag = dataclasses.replace(tag)
    new_tag.tag_id = new_id
    # data_fields/custom_fields are shared references after replace(); copy before mutating so we never
    # alter the original tag the caller may still hold.
    if (tag.data_fields or {}).get("id") is not None or (tag.original_schema or "").upper() == "TDG":
        new_tag.data_fields = dict(tag.data_fields or {})
        new_tag.data_fields["id"] = new_id
    else:
        new_tag.custom_fields = dict(tag.custom_fields or {})
        new_tag.custom_fields["id"] = new_id
    return new_tag


def _collect_paths(paths: list[str]) -> list[Path]:
    """Expand the given paths into a flat list of ``.py`` files."""
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            if p.name.endswith(".py"):
                files.append(p)
        elif p.is_dir():
            files.extend(sorted(f for f in p.rglob("*.py")))
        else:
            logger.warning("Path does not exist, skipping: %s", raw)
    return files


def run(
    paths: list[str],
    *,
    dry_run: bool = False,
    check: bool = False,
    counter_root: Path | None = None,
    writer: Callable[[str], None] = print,
) -> tuple[int, IdRunResult]:
    """Run the ``id`` command.

    Args:
        paths: Files or directories to scan. Directories are searched recursively for ``*.py``.
        dry_run: Report what would be assigned but write nothing (neither source nor counter).
        check: Assign nothing; exit nonzero if any taggable tag is missing an id. For CI / pre-commit.
        counter_root: Override the project root used to locate ``.pycodetags_ids`` (tests).
        writer: Sink for human-readable output (defaults to ``print``).

    Returns:
        ``(exit_code, result)``. Exit code is 0 on success, 1 when ``--check`` finds a missing id.
    """
    config = get_code_tags_config()
    active = config.active_schemas()

    # Build the candidate schema list (primary + any active plugin schemas, e.g. TDG) and a lookup.
    schemas: list[DataTagSchema] = [PureDataSchema]
    for extra in get_active_schemas(active):
        if extra.get("name") != PureDataSchema.get("name"):
            schemas.append(extra)
    schemas_by_name: dict[str, DataTagSchema] = {s.get("name", "").upper(): s for s in list_available_schemas()}
    schemas_by_name.setdefault("PUREDATA", PureDataSchema)

    counter = IdCounter.load(counter_root)
    result = IdRunResult()

    files = _collect_paths(paths)
    # Per file: list of (old_tag, new_tag, serializer) we will apply together.
    pending: dict[str, list[tuple[DATA, DATA, Callable[[DATA], str]]]] = defaultdict(list)
    missing_for_check: list[DATA] = []

    for file in files:
        raw_tags = list(iterate_comments_from_file(str(file), schemas=schemas, include_folk_tags="folk" in active))
        converted: list[DATA] = []
        for raw in raw_tags:
            origin = (raw.get("original_schema") or "").upper()
            schema = schemas_by_name.get("TDG", PureDataSchema) if origin == "TDG" else PureDataSchema
            converted.append(convert_data_tag_to_data_object(raw, schema))
        # Several active schemas can match the same block; collapse those duplicates so we assign one
        # id per physical tag and never mutate the same offsets twice.
        deduped = dedup_data_objects(converted)

        # Defensive safety net: the parser assigns *per-tag* offsets, so two distinct tags in one
        # comment block normally have distinct offsets and can each be mutated safely (the mutator
        # applies them end-to-start). If, despite that, two distinct tags still report identical
        # offsets (a parser edge case), refuse to mutate them rather than risk clobbering one with the
        # other -- the conservative choice the Risk Register calls for.
        offset_counts: dict[tuple[int, int, int, int] | None, int] = defaultdict(int)
        for tag in deduped:
            offset_counts[tag.offsets] += 1

        for tag in deduped:
            origin = (tag.original_schema or "").upper()
            result.scanned += 1

            kind, _value = resolve_identity(tag, _schema_for_tag(tag, schemas_by_name))
            if kind == "tracker":
                result.skipped_have_issue += 1
                continue
            if kind == "id":
                result.skipped_have_id += 1
                continue

            # No durable id yet: this tag needs one.
            if check:
                missing_for_check.append(tag)
                continue

            if tag.offsets is not None and offset_counts[tag.offsets] > 1:
                result.skipped_shared_block += 1
                logger.warning(
                    "Skipping tag sharing a comment block with another tag at %s: %r "
                    "(cannot rewrite one tag in a shared block safely)",
                    file,
                    tag.comment,
                )
                continue

            # First-time records: adopt any id already in source (none here by definition) and allocate.
            content_id = content_identity_for_data(tag, _schema_for_tag(tag, schemas_by_name))

            if origin == "TDG" and "TDG" not in schemas_by_name:
                # TDG tag but the TDG schema/serializer is not available — cannot safely rewrite.
                result.skipped_unsupported += 1
                logger.warning("Skipping TDG tag (TDG schema not active) at %s: %r", file, tag.comment)
                continue

            new_id = counter.allocate(content_id)
            new_tag = _with_id(tag, new_id)
            serializer = _tdg_serializer if origin == "TDG" else DATA.as_data_comment
            pending[str(file)].append((tag, new_tag, serializer))
            result.assigned += 1
            result.assignments.append((content_id, new_id))

    if check:
        if missing_for_check:
            writer(f"{len(missing_for_check)} tag(s) missing an id:")
            for tag in missing_for_check:
                writer(f"  {tag.terminal_link()}  {tag.code_tag}: {tag.comment}")
            return 1, result
        writer(f"All {result.scanned} tag(s) have an id.")
        return 0, result

    if dry_run:
        writer(f"[dry-run] Would assign {result.assigned} id(s) across {len(pending)} file(s):")
        for file_str, items in pending.items():
            for _old, new_tag, _ser in items:
                writer(f"  {file_str}: id={new_tag.tag_id}  {new_tag.code_tag}: {new_tag.comment}")
        _print_summary(writer, result, dry_run=True)
        return 0, result

    # Apply mutations per file. A single serializer is used per file group; all TDG tags share the TDG
    # serializer and all PEP-350 tags share as_data_comment, so we split each file's mutations by
    # serializer to keep apply_mutations' single-serializer contract.
    for file_str, items in pending.items():
        by_serializer: dict[Callable[[DATA], str], list[tuple[DATA, DATA | None]]] = defaultdict(list)
        for old, new, item_serializer in items:
            by_serializer[item_serializer].append((old, new))
        for group_serializer, muts in by_serializer.items():
            mutator.apply_mutations(file_str, muts, serializer=group_serializer)
        result.files_changed.append(file_str)

    if result.assigned and not dry_run:
        counter.save()

    _print_summary(writer, result, dry_run=False)
    return 0, result


def _print_summary(writer: Callable[[str], None], result: IdRunResult, *, dry_run: bool) -> None:
    """Print the closing summary line(s)."""
    prefix = "[dry-run] " if dry_run else ""
    writer(
        f"{prefix}Scanned {result.scanned} tag(s); "
        f"assigned {result.assigned}; "
        f"skipped {result.skipped_have_id} with id, "
        f"{result.skipped_have_issue} with issue, "
        f"{result.skipped_shared_block} sharing a block, "
        f"{result.skipped_unsupported} unsupported."
    )
    if result.files_changed:
        writer(f"{prefix}Changed {len(result.files_changed)} file(s).")
