"""
TDG (ribtoks/tdg) style code-tag parser.

A TDG tag spans up to three zones inside a comment block::

    # TODO: This is the title of the issue to create     <- Zone 1: anchor (type + title)
    # category=SomeCategory issue=123 estimate=30m        <- Zone 2: property line (optional)
    # This is a multiline description of the issue         <- Zone 3: body (zero or more lines)
    # that becomes the issue body

Parsing rules (see ``spec/id_and_tdg.md`` Part 4):

1. **Zone 1** is a line matching ``# TAG: title`` where TAG is in the schema's matching tags.
2. **Zone 2** is the *immediately following* comment line, and only if it passes
   :func:`is_property_line` (a heuristic: >50% of its tokens look like ``key=value``). Otherwise there
   is no property line and that line is body.
3. **Zone 3** accumulates subsequent comment lines until a non-comment line, the end of the block, or
   a *new anchor* (``# TODO:`` / ``# FIXME:`` ...). A new anchor finalizes the current tag and starts
   another.

This module is pure: no filesystem access, no config. Offsets are 0-based and **relative to the
``source`` string passed in** (typically a single comment block); callers add the block base offset.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Generator
from pathlib import Path

from pycodetags.data_tags.data_tags_methods import DataTag
from pycodetags.data_tags.data_tags_parsers import parse_fields
from pycodetags.data_tags.data_tags_schema import DataTagSchema

logger = logging.getLogger(__name__)

__all__ = ["iterate_comments", "is_property_line", "as_tdg_comment"]

# A line like `# TODO: title` or `# TODO title`. Group 1 is the tag, group 2 the title text.
_ANCHOR_RE = re.compile(r"^[ \t]*#\s*([A-Za-z][A-Za-z0-9_]*)\s*:\s*(.*)$")

# A single `key=value` token (value is non-whitespace; quoting handled later by parse_fields).
_PROPERTY_TOKEN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S+$")

# Strip exactly one leading `# ` (or `#`) from a comment line, preserving the rest verbatim.
_COMMENT_PREFIX_RE = re.compile(r"^[ \t]*#[ \t]?")


def is_property_line(comment_text: str) -> bool:
    """Heuristic: does this comment line look like a TDG ``key=value`` property line?

    The line must be a comment, contain at least one token, and have a strict majority (>50%) of its
    whitespace-separated tokens matching ``key=value``. This prevents an English sentence that merely
    contains an ``=`` (e.g. ``# Use the old method=foo approach``) from being mistaken for properties.

    Args:
        comment_text: A single line, with or without its leading ``#``.

    Returns:
        True if the line should be parsed as a property line.

    Examples:
        >>> is_property_line("# category=core issue=123 estimate=30m")
        True
        >>> is_property_line("# Use the old method=foo approach here")
        False
        >>> is_property_line("# just a normal description")
        False
        >>> is_property_line("# issue=123")
        True
    """
    stripped = _COMMENT_PREFIX_RE.sub("", comment_text).strip()
    if not stripped:
        return False
    tokens = stripped.split()
    if not tokens:
        return False
    matches = sum(1 for t in tokens if _PROPERTY_TOKEN_RE.match(t))
    return matches > len(tokens) / 2


def _is_comment_line(line: str) -> bool:
    return line.lstrip().startswith("#")


def _clean_body_line(line: str) -> str:
    """Strip exactly one leading ``# `` from a body line. A bare ``#`` becomes an empty string."""
    return _COMMENT_PREFIX_RE.sub("", line)


def _matches_a_tag(tag: str, valid_tags: list[str]) -> bool:
    return tag in valid_tags


def iterate_comments(source: str, source_file: Path | None, schemas: list[DataTagSchema]) -> Generator[DataTag]:
    """Yield TDG-style :class:`DataTag` objects found in ``source``.

    Args:
        source: The text to scan (typically one comment block).
        source_file: Provenance for the produced tags.
        schemas: Candidate schemas; the first whose ``matching_tags`` contains the anchor tag wins.

    Yields:
        DataTag dicts with ``original_schema == "TDG"`` and block-relative offsets.
    """
    if "\r\n" in source:
        lines = source.split("\r\n")
    else:
        lines = source.split("\n")

    i = 0
    n = len(lines)
    while i < n:
        anchor = _ANCHOR_RE.match(lines[i])
        if not anchor:
            i += 1
            continue

        code_tag = anchor.group(1).strip()

        # Find the schema that recognizes this tag.
        active_schema: DataTagSchema | None = None
        for schema in schemas:
            if _matches_a_tag(code_tag, schema.get("matching_tags", [])):
                active_schema = schema
                break
        if active_schema is None:
            i += 1
            continue

        # Set of tag names that count as a terminating "new anchor" within a body. A line like
        # `# NOTE:` is NOT a recognized tag, so it is body text, not a boundary.
        valid_tags = set()
        for schema in schemas:
            valid_tags.update(schema.get("matching_tags", []))

        tag, next_i = _parse_one_tag(
            lines, i, code_tag, anchor.group(2).strip(), active_schema, source_file, valid_tags
        )
        yield tag
        # Guarantee forward progress even if _parse_one_tag returns the same index.
        i = next_i if next_i > i else i + 1


def _is_recognized_anchor(line: str, valid_tags: set[str]) -> bool:
    """True if ``line`` is an anchor whose tag is a recognized (valid) tag name."""
    m = _ANCHOR_RE.match(line)
    return bool(m and m.group(1).strip() in valid_tags)


def _parse_one_tag(
    lines: list[str],
    anchor_idx: int,
    code_tag: str,
    title: str,
    schema: DataTagSchema,
    source_file: Path | None,
    valid_tags: set[str],
) -> tuple[DataTag, int]:
    """Parse a single TDG tag starting at ``anchor_idx``. Returns (tag, index_after_tag)."""
    start_line = anchor_idx
    start_char = lines[anchor_idx].find("#")

    idx = anchor_idx + 1
    n = len(lines)

    # Zone 2: optional property line (must be the immediately-following comment line, and not a
    # recognized new anchor).
    field_string = ""
    if (
        idx < n
        and _is_comment_line(lines[idx])
        and not _is_recognized_anchor(lines[idx], valid_tags)
        and is_property_line(lines[idx])
    ):
        field_string = _COMMENT_PREFIX_RE.sub("", lines[idx]).strip()
        idx += 1

    # Zone 3: body lines until a non-comment line, a recognized new anchor, or end of block. An
    # unrecognized `Word:` line (e.g. `# NOTE:`) is body text, not a boundary.
    body_lines: list[str] = []
    while idx < n:
        line = lines[idx]
        if not _is_comment_line(line):
            break
        if _is_recognized_anchor(line, valid_tags):  # a recognized new anchor ends this tag
            break
        body_lines.append(_clean_body_line(line))
        idx += 1

    # The last consumed line is idx-1 (anchor at minimum).
    end_line = idx - 1
    end_char = len(lines[end_line].rstrip())

    fields = parse_fields(field_string, schema, strict=False)

    body = "\n".join(body_lines).strip("\n")
    if body:
        fields["custom_fields"]["body"] = body
    if title:
        fields["custom_fields"]["title"] = title

    tag: DataTag = {
        "code_tag": code_tag,
        "comment": title,  # backwards compat: comment mirrors the title
        "fields": fields,
        "file_path": str(source_file) if source_file else None,
        "original_text": "\n".join(lines[start_line : end_line + 1]),
        "original_schema": "TDG",
        "offsets": (start_line, start_char, end_line, end_char),
    }
    return tag, idx


def as_tdg_comment(
    *,
    code_tag: str,
    title: str | None,
    body: str | None = None,
    properties: dict[str, object] | None = None,
) -> str:
    """Serialize a tag back into TDG comment form.

    Produces::

        # TODO: {title}
        # key=value key=value        (only if there are non-empty properties)
        # {body line 1}
        # {body line 2}

    ``title``/``body`` are never emitted as properties even if present in ``properties``. Property
    values containing whitespace are double-quoted. Round-trips with :func:`iterate_comments`.

    Args:
        code_tag: The tag name (e.g. ``"TODO"``).
        title: The first-line title text.
        body: Optional multi-line body.
        properties: Optional ``key=value`` data (e.g. ``issue``, ``category``, ``estimate``, ``id``).

    Returns:
        A multi-line comment string (no trailing newline).
    """
    out: list[str] = [f"# {code_tag.upper()}: {title or ''}".rstrip()]

    prop_parts: list[str] = []
    for key, value in (properties or {}).items():
        if key in ("title", "body"):
            continue
        if value is None or str(value).strip() == "":
            continue
        text = str(value)
        if any(c.isspace() for c in text):
            text = f'"{text}"'
        prop_parts.append(f"{key}={text}")
    if prop_parts:
        out.append("# " + " ".join(prop_parts))

    if body:
        for line in body.split("\n"):
            out.append(f"# {line}".rstrip())

    return "\n".join(out)
