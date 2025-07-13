"""
Abstract data serialization format, of which PEP-350 is one schema.

In scope:
    - parsing a data tag as a data serialization format.
    - defining a schema
    - domain free concepts
    - Parsing python to extract # comments, be it AST or regex or other strategy
    - Round tripping to and from data tag format
    - Equivalence checking by value
    - Merging and promoting fields among default, data and custom.

Out of scope:
    - File system interaction
    - Any particular schema (PEP350 code tags, discussion tags, documentation tags, etc)
    - Domain specific concepts (users, initials, start dates, etc)
    - Docstring style comments and docstrings

Inputs:
    - A block of valid python comment text
    - A schema

Outputs:
    - A python data structure that represents a data structure

Half-hearted goal:
    - Minimize python concepts so this can be implemented in Javascript, etc.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # noqa

logger = logging.getLogger(__name__)


class DataTagSchema(TypedDict):
    """
    Data for interpreting a domain specific code tag.
    """

    name: str

    matching_tags: list[str]
    """What tag names match, e.g. TODO, FIXME are issue tracker tags"""

    default_fields: dict[str, str]
    """type:name, e.g. str:assignees"""

    data_fields: dict[str, str]
    """name:type, e.g. priority:str"""

    data_field_aliases: dict[str, str]
    """name:alias, e.g. priority:p"""

    field_infos: dict[str, FieldInfo]
    """ALl info about a field, a field could appear in defaults, data"""


class FieldInfo(TypedDict):
    name: str
    """Name as written in tag, no spaces"""
    data_type: str
    """str, int, list[str], str|list[str]"""
    valid_values: list[str]
    """Default range, override with config"""
    label: str
    """What to display in UI"""
    description: str
    """What does this field mean"""
    aliases: list[str]
    """Alternate names and abbreviations for field"""

    value_on_new: str
    """Value on first appearance of data tag, e.g. originator={git-user}"""
    value_on_blank: str
    """Value of last resort that is reasonable at all times, e.g. priority=medium"""
    value_on_delete: str
    """Value of missing field after data tag is deleted, e.g. status=closed"""


class DataTagFields(TypedDict):
    """Rules for interpreting the fields part of a code tag"""

    unprocessed_defaults: list[str]

    # When deserializating a field value could appear in default, data and custom field positions.
    default_fields: dict[str, list[Any]]
    """Field without label identified by data type, range or fallback, e.g. user and date"""

    # TODO: support dict[str, int | date | str | list[int, date, str]] ? <matth 2025-07-04
    #  category:schema priority:high status:development release:1.0.0 iteration:1>
    data_fields: dict[str, Any]
    """Expected fields with labels, e.g. category, priority"""

    custom_fields: dict[str, str]
    """Key value pairs, e.g. SAFe program increment number"""

    identity_fields: list[str]
    """Fields which combine to form an identity for the tag, e.g. originator, origination_date"""


def merge_schemas(base: DataTagSchema, override: DataTagSchema) -> DataTagSchema:
    """
    Merge two DataTagSchemas into one.

    - Fields from `override` will replace or extend those from `base`
    - Lists like `matching_tags` are combined without duplication
    - Dicts are shallow merged with `override` taking precedence
    """
    merged: DataTagSchema = deepcopy(base)

    merged["name"] = override.get("name", merged["name"])

    merged["matching_tags"] = list(sorted(set(merged.get("matching_tags", []) + override.get("matching_tags", []))))

    for key in ("default_fields", "data_fields", "data_field_aliases"):
        base_dict = merged.get(key, {})  # type: ignore
        override_dict = override.get(key, {})  # type: ignore
        merged[key] = {**base_dict, **override_dict}  # type: ignore

    return merged


def data_fields_as_list(schema: DataTagSchema):
    return list(schema["data_fields"].keys())
