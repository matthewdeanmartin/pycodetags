"""Explicit TDG entry points backed by the shared format parser and serializer."""

from __future__ import annotations

from pathlib import Path

from pycodetags.data_tags.data_tags_classes import DATA
from pycodetags.data_tags.formats import PREFIX, parse_block, property_line, serialize_tag
from pycodetags.exceptions import SchemaError
from pycodetags.schemas import TDGSchema, validate_schema

__all__ = ["iterate_comments", "is_property_line", "as_tdg_comment"]


def is_property_line(comment_text: str) -> bool:
    """A TDG property line begins with key=value, with optional comment prefix."""
    return property_line(PREFIX.sub("", comment_text, count=1))


def iterate_comments(source: str, source_file: Path | None, schemas: list):
    """Parse a block with an explicitly selected TDG schema."""
    if len(schemas) != 1:
        raise SchemaError("Select exactly one TDG schema.")
    schema = validate_schema(schemas[0])
    if schema["format"] != "TDG":
        raise SchemaError("The TDG parser requires format='TDG'.")
    for tag in parse_block(source, schema):
        tag["file_path"] = str(source_file) if source_file else None
        tag["schema"] = schema
        yield tag


def as_tdg_comment(
    *, code_tag: str, title: str | None, body: str | None = None, properties: dict[str, object] | None = None
) -> str:
    """Render TDG explicitly, including properly quoted properties and literal body lines."""
    return serialize_tag(DATA(code_tag=code_tag.upper(), title=title, body=body, data_fields=properties), TDGSchema)
