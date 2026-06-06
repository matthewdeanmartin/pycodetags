"""
Data tag identity.

Identity is layered into three tiers (see ``spec/id_and_tdg.md``):

1. **Content identity** - a stable hash of the tag's semantic fields. Always available, free to
   compute, and changes only when the tag's *meaningful* text changes. Used for dedup and for
   matching a freshly parsed tag back to a previously seen one.
2. **Local identity** (``id=N``) - a short integer assigned lazily by a tool, never during parsing.
3. **Tracker identity** (``issue=NNN`` / ``tracker=<url>``) - the canonical id when present.

This module is schema-agnostic and contains no file-system interaction and no hard parsing.
"""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Any

from pycodetags.data_tags.data_tags_schema import DataTagSchema

if TYPE_CHECKING:
    from pycodetags.data_tags.data_tags_classes import DATA
    from pycodetags.data_tags.data_tags_methods import DataTag

logger = logging.getLogger(__name__)

# Length of the truncated hex digest used for content identity.
_CONTENT_HASH_LEN = 12


def _normalize(value: Any) -> str:
    """Normalize a field value to a stable string for hashing.

    Whitespace is collapsed. Lists are joined with commas (order preserved). ``None`` becomes ``""``.
    Values are case-sensitive on purpose.
    """
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ",".join(_normalize(v) for v in value)
    return " ".join(str(value).split())


def _hash_parts(parts: list[str]) -> str:
    """Hash an ordered list of normalized string parts into a short hex digest."""
    hasher = hashlib.sha256()
    # Use a separator that cannot appear after normalization collapses whitespace runs,
    # so ("a", "bc") and ("ab", "c") do not collide.
    hasher.update("\x00".join(parts).encode("utf-8"))
    return hasher.hexdigest()[:_CONTENT_HASH_LEN]


def content_identity(tag: DataTag, schema: DataTagSchema) -> str:
    """Compute a stable short hash of the tag's identity fields.

    The hash always includes ``code_tag`` and ``comment``. If the schema declares
    ``identity_fields``, those ``data_fields`` values are appended in the listed order. Volatile or
    derived fields (status, priority, assignee, offsets, file path, ...) are intentionally excluded
    unless a schema explicitly lists them in ``identity_fields``.

    Args:
        tag: The parsed data tag.
        schema: The schema, whose ``identity_fields`` drive which fields participate.

    Returns:
        A 12-character hex digest, e.g. ``"a1b2c3d4e5f6"``.
    """
    parts: list[str] = [
        _normalize(tag.get("code_tag")),
        _normalize(tag.get("comment")),
    ]

    identity_fields = schema.get("identity_fields") or []
    if identity_fields:
        fields: dict[str, Any] = dict(tag.get("fields") or {})
        data_fields = fields.get("data_fields", {})
        custom_fields = fields.get("custom_fields", {})
        for name in identity_fields:
            # Identity-bearing tracker fields like ``issue`` are part of identity when present, but
            # a *blank* identity field must not destabilize the hash, so blanks normalize to "".
            value = data_fields.get(name)
            if value is None:
                value = custom_fields.get(name)
            parts.append(_normalize(value))

    return _hash_parts(parts)


def content_identity_for_data(tag: DATA, schema: DataTagSchema) -> str:
    """Compute content identity for a strongly-typed :class:`DATA` object.

    Mirrors :func:`content_identity` but reads from a ``DATA`` instance rather than a ``DataTag``
    dict. The attribute (e.g. ``tag.priority``) is preferred, falling back to ``data_fields`` then
    ``custom_fields`` so it works regardless of how fully promoted the object is.
    """
    parts: list[str] = [_normalize(tag.code_tag), _normalize(tag.comment)]

    identity_fields = schema.get("identity_fields") or []
    for name in identity_fields:
        value = getattr(tag, name, None)
        if value is None:
            value = (tag.data_fields or {}).get(name)
        if value is None:
            value = (tag.custom_fields or {}).get(name)
        parts.append(_normalize(value))

    return _hash_parts(parts)


def _field_value(tag: DATA, *names: str) -> str | None:
    """Return the first non-blank value for any of ``names``, checking attribute then dicts."""
    for name in names:
        value = getattr(tag, name, None)
        if value is None:
            value = (tag.data_fields or {}).get(name)
        if value is None:
            value = (tag.custom_fields or {}).get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def resolve_identity(tag: DATA, schema: DataTagSchema | None = None) -> tuple[str, str]:
    """Resolve the canonical identity of a tag *right now*.

    Resolution order: tracker (``issue`` / ``tracker``) > local (``id`` / ``tag_id``) > content hash.

    Args:
        tag: The strongly-typed tag.
        schema: Optional schema used for the content-hash fallback. If omitted, the content hash is
            computed from ``code_tag`` + ``comment`` only.

    Returns:
        A ``(kind, value)`` tuple where ``kind`` is one of ``"tracker"``, ``"id"``, ``"content"``.
    """
    tracker = _field_value(tag, "issue", "tracker")
    if tracker:
        return ("tracker", tracker)

    local = _field_value(tag, "tag_id", "id")
    if local:
        return ("id", local)

    if schema is not None:
        return ("content", content_identity_for_data(tag, schema))

    return ("content", _hash_parts([_normalize(tag.code_tag), _normalize(tag.comment)]))
