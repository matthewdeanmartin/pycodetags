"""Validated update/delete batches with byte-preserving, single-file replacement."""

from __future__ import annotations

import io
import os
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

from pycodetags.common_interfaces import dumps
from pycodetags.data_tags import DATA
from pycodetags.exceptions import DataTagError
from pycodetags.source_io import logical_text, read_python_source, replace_source, text_digest


def source_lines(text: str) -> list[str]:
    """Split physical lines without treating other Unicode whitespace as line breaks."""
    return io.StringIO(text, newline="").readlines()


def line_ending(line: str) -> str:
    """Return the physical line terminator, or an empty string at an unterminated EOF."""
    return line[len(line.rstrip("\r\n")) :]


def format_replacement(text: str, indentation: str, newline: str) -> str:
    """Indent continuation comments without copying inline executable code or stripping body text."""
    lines = logical_text(text).split("\n")
    if any(not line.lstrip(" \t").startswith("#") for line in lines):
        raise DataTagError("Replacement must contain only comment lines, without a trailing newline.")
    return (newline + indentation).join(lines)


def apply_mutations(
    file_path: str | os.PathLike[str],
    mutations: Sequence[tuple[DATA, DATA | None]],
    serializer: Callable[[DATA], str] | None = None,
) -> None:
    """Validate and apply one file's updates/deletes together.

    Args:
        file_path: Source file to replace once after validating the complete batch.
        mutations: Parsed old records paired with replacements, or None for deletion.
        serializer: Optional explicit comment renderer; otherwise preserve each record's schema.

    Rejects stale snapshots, wrong files, invalid/overlapping spans, and invalid rendering before
    writing. Existing bytes outside the addressed spans are preserved. Deletion retains the final
    line terminator and any prefix before the tag, including inline executable code. Reparse after
    writing before making another batch. This requires one writer; it is not a multi-file transaction.
    """
    snapshot = read_python_source(file_path)
    if not mutations:
        return
    lines = source_lines(snapshot.text)
    starts = []
    total = 0
    for line in lines:
        starts.append(total)
        total += len(line)
    digest = text_digest(snapshot.text)
    newline = next((line_ending(line) for line in lines if line_ending(line)), "\n")
    replacements = []
    for old, new in mutations:
        if not isinstance(old, DATA) or (new is not None and not isinstance(new, DATA)):
            raise TypeError("mutations must contain (DATA, DATA | None) pairs.")
        if old.file_path is not None and Path(old.file_path).resolve() != snapshot.path.resolve():
            raise DataTagError("Tag belongs to a different source file.")
        if old.source_digest is None or old.source_digest != digest:
            raise DataTagError("Tag mismatch: source snapshot is stale or missing; reparse before writing.")
        if old.source_bytes_digest is not None and old.source_bytes_digest != snapshot.digest:
            raise DataTagError("Tag mismatch: source bytes changed; reparse before writing.")
        offsets = old.offsets
        if not isinstance(offsets, tuple) or len(offsets) != 4 or any(type(value) is not int for value in offsets):
            raise DataTagError("Invalid tag offsets; expected four integer coordinates.")
        first, column, last, end = offsets
        if not (0 <= first <= last < len(lines)):
            raise DataTagError("Invalid tag offsets: line outside source.")
        if not (0 <= column <= len(lines[first].rstrip("\r\n")) and 0 <= end <= len(lines[last].rstrip("\r\n"))):
            raise DataTagError("Invalid tag offsets: column outside source.")
        start, stop = starts[first] + column, starts[last] + end
        if start >= stop:
            raise DataTagError("Invalid tag offsets: empty or reversed span.")
        actual = snapshot.text[start:stop]
        if old.original_text is None or logical_text(actual) != logical_text(old.original_text):
            raise DataTagError("Tag mismatch: text at the stored span differs from the parsed tag.")
        if not actual.startswith("#"):
            raise DataTagError("Invalid tag offsets: span must begin at a comment.")
        rendered = ""
        if new is not None:
            selected = new.schema if new.schema is not None else old.schema
            rendered = serializer(new) if serializer is not None else dumps(new, schema=selected)
            prefix = lines[first][:column]
            indentation = prefix[: len(prefix) - len(prefix.lstrip(" \t"))]
            rendered = format_replacement(rendered, indentation, line_ending(lines[first]) or newline)
        replacements.append((start, stop, rendered))
    replacements.sort(key=lambda item: item[0])
    for previous, current in zip(replacements, replacements[1:]):
        if current[0] < previous[1]:
            raise DataTagError("Overlapping tag mutations; each source span may be changed only once.")
    pieces = []
    cursor = 0
    for start, stop, rendered in replacements:
        pieces.extend((snapshot.text[cursor:start], rendered))
        cursor = stop
    pieces.append(snapshot.text[cursor:])
    replace_source(snapshot, "".join(pieces))


def update_tags(file_path: str | os.PathLike[str], updates: Sequence[tuple[DATA, DATA]]) -> None:
    """Update parsed records in one validated file batch; use dataclasses.replace to retain fields."""
    apply_mutations(file_path, updates)


def delete_tags(file_path: str | os.PathLike[str], tags_to_delete: Sequence[DATA]) -> None:
    """Delete exactly the parsed tag spans, leaving surrounding source text intact."""
    apply_mutations(file_path, [(tag, None) for tag in tags_to_delete])


def replace_with_strings(file_path: str | os.PathLike[str], replacements: Sequence[tuple[DATA, str]]) -> None:
    """Update titles while retaining each record's body, metadata, identity, and schema."""
    apply_mutations(file_path, [(old, replace(old, title=title, comment=title)) for old, title in replacements])


def insert_tags(file_path: str | os.PathLike[str], insertions: Sequence[tuple[int, DATA, int]]) -> None:
    """Insert before blank lines, or at EOF, using one validated source replacement.

    Each tuple contains a one-based line number, a record with an explicit schema, and a nonnegative
    space indentation count. Duplicate positions are rejected. The input sequence is never sorted
    in place. Existing blank lines are retained.
    """
    snapshot = read_python_source(file_path)
    if not insertions:
        return
    lines = source_lines(snapshot.text)
    newline = next((line_ending(line) for line in lines if line_ending(line)), "\n")
    prepared = {}
    for number, tag, indentation in insertions:
        if type(number) is not int or not 1 <= number <= len(lines) + 1:
            raise ValueError(f"Invalid line number: {number}.")
        if number <= len(lines) and lines[number - 1].strip():
            raise ValueError(f"Cannot insert tag at line {number}. Line is not blank.")
        if number in prepared:
            raise ValueError(f"Duplicate insertion line: {number}.")
        if type(indentation) is not int or indentation < 0:
            raise ValueError("Indentation must be a nonnegative integer.")
        ending = line_ending(lines[number - 1]) if number <= len(lines) else newline
        ending = ending or newline
        prefix = " " * indentation
        rendered = prefix + format_replacement(dumps(tag), prefix, ending)
        prepared[number] = rendered + (ending if number <= len(lines) or not lines or line_ending(lines[-1]) else "")
    pieces = []
    for number, line in enumerate(lines, 1):
        pieces.extend((prepared.get(number, ""), line))
    if len(lines) + 1 in prepared:
        if lines and not line_ending(lines[-1]):
            pieces.append(newline)
        pieces.append(prepared[len(lines) + 1])
    replace_source(snapshot, "".join(pieces))
