"""Built-in schemas and explicit schema selection."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from pycodetags.data_tags.data_tags_schema import DataTagSchema
from pycodetags.exceptions import SchemaError

TAG_NAMES = ["TODO", "FIXME", "BUG", "HACK", "NOTE", "XXX", "WARNING", "CAUTION", "DONE", "DATA", "REQ", "IDEA", "RFE"]
TAG_FIELDS = {
    "id": "str",
    "issue": "str",
    "tracker": "str",
    "category": "str",
    "estimate": "str",
    "author": "str",
    "origination_date": "str",
    "assignee": "str",
    "priority": "str",
    "status": "str",
}

TDGSchema: DataTagSchema = {
    "name": "TDG",
    "format": "TDG",
    "matching_tags": TAG_NAMES.copy(),
    "default_fields": {},
    "data_fields": TAG_FIELDS.copy(),
    "data_field_aliases": {"cat": "category"},
    "field_infos": {},
    "identity_fields": [],
}
PEP350Schema: DataTagSchema = dict(deepcopy(TDGSchema), name="PEP350", format="PEP350")


def validate_schema(schema: DataTagSchema) -> DataTagSchema:
    """Require a named schema with an explicit wire format and recognized tag names."""
    if not isinstance(schema, dict) or not schema.get("name") or schema.get("format") not in ("TDG", "PEP350"):
        raise SchemaError("A schema must name its format explicitly: 'TDG' or 'PEP350'.")
    tags = schema.get("matching_tags")
    if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) and tag for tag in tags):
        raise SchemaError("A schema must supply a non-empty matching_tags list.")
    for key in ("data_fields", "default_fields", "data_field_aliases", "field_infos"):
        if not isinstance(schema.get(key), dict):
            raise SchemaError(f"A schema must supply a {key} dictionary.")
    return deepcopy(schema)


def named_schema(name: str) -> DataTagSchema:
    """Resolve an explicitly selected name. Built-in names are reserved for the core schemas."""
    if not isinstance(name, str):
        raise SchemaError("Schema selection must be a schema name or definition.")
    for builtin in (TDGSchema, PEP350Schema):
        if name.casefold() == builtin["name"].casefold():
            return validate_schema(builtin)
    from pycodetags.common_interfaces import list_available_schemas

    matches = [schema for schema in list_available_schemas() if schema["name"].casefold() == name.casefold()]
    if len(matches) != 1:
        raise SchemaError(f"Unknown or ambiguous schema {name!r}; choose TDG, PEP350, or a registered schema.")
    return validate_schema(matches[0])


def resolve_schema(schema: str | DataTagSchema | None = None, file_path: str | Path | None = None) -> DataTagSchema:
    """Use an explicit argument or project configuration; never inspect source to guess a schema."""
    if schema is None:
        from pycodetags.app_config import get_code_tags_config

        schema = get_code_tags_config().schema_for_path(file_path)
    return named_schema(schema) if isinstance(schema, str) else validate_schema(schema)
