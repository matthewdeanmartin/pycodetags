"""
The ``pycodetags id`` command: lazily assign stable local ids (``id=N``) to data tags.

This is the *tool-driven* half of the identity model. The user
writes plain tags with no ``id``. When durable identity is needed, this command:

1. scans the given paths for data tags,
2. skips tags that already have an ``id``; tracker-linked tags still need local IDs,
3. reserves existing IDs, then allocates integers from the per-project counter (``.pycodetags_ids``),
4. saves the reservations before writing source (failed writes may leave gaps),
5. rewrites comments to add ``id=N`` in their original PEP-350 or TDG syntax.

Assignment scans the source files. Use ``TagIndex`` for repeated indexed lookups after refreshing.

Both schemas are built in. Each file uses schema= or explicit project/path configuration.
"""

from __future__ import annotations

import dataclasses
import logging
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from pycodetags import mutator
from pycodetags.aggregate import dedup_data_objects
from pycodetags.data_tags import DATA, DataTagSchema, convert_data_tag_to_data_object, iterate_comments_from_file
from pycodetags.data_tags.identity import content_identity_for_data, field_value, resolve_identity
from pycodetags.exceptions import DataTagError
from pycodetags.identity_counter import IdCounter

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class IdRunResult:
    """Summary of an ``id`` command run, returned for testing and reporting."""

    scanned: int = 0
    assigned: int = 0
    skipped_have_id: int = 0
    skipped_unsupported: int = 0
    skipped_shared_block: int = 0
    files_changed: list[str] = dataclasses.field(default_factory=list)
    # tag content-id -> newly assigned id, in assignment order (for --dry-run reporting and tests).
    assignments: list[tuple[str, str]] = dataclasses.field(default_factory=list)


def tdg_serializer(tag: DATA) -> str:
    """Explicitly render TDG using the shared serializer."""
    from pycodetags.common_interfaces import dumps

    return dumps(tag, schema="TDG")


def with_id(tag: DATA, new_id: str) -> DATA:
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


def collect_paths(paths: list[str], exclude: list[str] | None = None, root: Path | None = None) -> list[Path]:
    """Expand Python source paths once, pruning explicitly excluded directories."""
    from pycodetags.app_config import get_code_tags_config
    from pycodetags.discovery import discover_files

    config = get_code_tags_config()
    base = root or config.pyproject_path.parent
    absolute = [Path(path).resolve() for path in paths]
    if any(not path.is_relative_to(base.resolve()) for path in absolute):
        import os

        base = Path(os.path.commonpath([str(path.parent) for path in absolute]))
    return discover_files(base, absolute, config.config.get("exclude", []) if exclude is None else exclude)


def run(
    paths: list[str],
    *,
    dry_run: bool = False,
    check: bool = False,
    counter_root: Path | None = None,
    writer: Callable[[str], None] = print,
    schema: str | DataTagSchema | None = None,
    exclude: list[str] | None = None,
) -> tuple[int, IdRunResult]:
    """Run the ``id`` command.

    Args:
        paths: Files or directories to scan. Directories are searched recursively for ``*.py``.
        dry_run: Report what would be assigned but write nothing (neither source nor counter).
        check: Assign nothing; exit nonzero if any taggable tag is missing an id. For CI / pre-commit.
        counter_root: Override the project root used to locate ``.pycodetags_ids`` (tests).
        exclude: Root-relative source exclusion patterns; otherwise use project configuration.
        schema: Explicit schema selection; otherwise use project configuration.
        writer: Sink for human-readable output (defaults to ``print``).

    Returns:
        ``(exit_code, result)``. Exit code is 0 on success, 1 when ``--check`` finds a missing id.
    """
    from pycodetags.schemas import resolve_schema

    counter = IdCounter.load(counter_root)
    result = IdRunResult()

    files = collect_paths(paths, exclude=exclude, root=counter_root)
    # Per file: list of (old_tag, new_tag, serializer) we will apply together.
    pending: dict[str, list[tuple[DATA, DATA]]] = defaultdict(list)
    missing_for_check: list[DATA] = []

    collected: dict[Path, list[DATA]] = {}
    seen_ids: dict[str, DATA] = {}
    for file in files:
        selected = resolve_schema(schema, file)
        raw_tags = list(iterate_comments_from_file(str(file), schemas=[selected], include_folk_tags=False))
        converted: list[DATA] = []
        for raw in raw_tags:
            converted.append(convert_data_tag_to_data_object(raw, selected))
        # Keep one assignment per physical source span.
        deduped = dedup_data_objects(converted)
        collected[file] = deduped
        for tag in deduped:
            local_id = field_value(tag, "tag_id", "id")
            if local_id is None:
                continue
            if local_id in seen_ids:
                previous = seen_ids[local_id]
                raise DataTagError(
                    f"Duplicate local id {local_id!r}: {previous.file_path}:{previous.offsets} "
                    f"and {tag.file_path}:{tag.offsets}. No files were changed."
                )
            seen_ids[local_id] = tag
            counter.record_existing(local_id, content_identity_for_data(tag, tag.schema))

    # Reserve all observed IDs before allocating, including IDs in later files or tracker-backed tags.
    for file, deduped in collected.items():

        # Defensive safety net: the parser assigns *per-tag* offsets, so two distinct tags in one
        # comment block normally have distinct offsets and can each be mutated safely (the mutator
        # applies them end-to-start). If, despite that, two distinct tags still report identical
        # offsets (a parser edge case), refuse to mutate them rather than risk clobbering one with the
        # other -- the conservative choice the Risk Register calls for.
        offset_counts: dict[tuple[int, int, int, int] | None, int] = defaultdict(int)
        for tag in deduped:
            offset_counts[tag.offsets] += 1

        for tag in deduped:
            result.scanned += 1

            kind = resolve_identity(tag, tag.schema)[0]
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
            content_id = content_identity_for_data(tag, tag.schema)

            new_id = counter.allocate(content_id)
            new_tag = with_id(tag, new_id)
            pending[str(file)].append((tag, new_tag))
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
            for _, new_tag in items:
                writer(f"  {file_str}: id={new_tag.tag_id}  {new_tag.code_tag}: {new_tag.comment}")
        print_summary(writer, result, dry_run=True)
        return 0, result

    # Persist reservations first: a later write failure must never allow reuse of allocated IDs.
    if result.assigned or seen_ids:
        counter.save()

    # All records for a file share one validated mutation batch.
    for file_str, items in pending.items():
        mutator.apply_mutations(file_str, items)
        result.files_changed.append(file_str)

    print_summary(writer, result, dry_run=False)
    return 0, result


def print_summary(writer: Callable[[str], None], result: IdRunResult, *, dry_run: bool) -> None:
    """Print the closing summary line(s)."""
    prefix = "[dry-run] " if dry_run else ""
    writer(
        f"{prefix}Scanned {result.scanned} tag(s); "
        f"assigned {result.assigned}; "
        f"skipped {result.skipped_have_id} with id, "
        f"{result.skipped_shared_block} sharing a block, "
        f"{result.skipped_unsupported} unsupported."
    )
    if result.files_changed:
        writer(f"{prefix}Changed {len(result.files_changed)} file(s).")
