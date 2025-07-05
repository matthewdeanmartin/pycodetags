"""
Converters for FolkTag and DataTag typed dicts to DATA class
"""

from __future__ import annotations

import logging
from typing import Any

from pycodetags.data_tags_classes import DATA
from pycodetags.data_tags_methods import promote_fields
from pycodetags.data_tags_schema import DataTag, DataTagSchema
from pycodetags.folk_code_tags import FolkTag

logger = logging.getLogger(__name__)


def convert_folk_tag_to_DATA(folk_tag: FolkTag, schema: DataTagSchema) -> DATA:  # pylint: disable=unused-argument
    """
    Convert a FolkTag to a DATA object. A DATA object does not attempt to
    convert domain specific fields to strongly typed properties/fields

    Args:
        folk_tag (FolkTag): The FolkTag to convert.
        schema (DataTagSchema): Which schema to force the folk tag into
    """
    kwargs = {
        "code_tag": folk_tag.get("code_tag"),
        "custom_fields": folk_tag.get("custom_fields"),
        "comment": folk_tag["comment"],  # required
        "file_path": folk_tag.get("file_path"),
        "line_number": folk_tag.get("line_number"),
        "original_text": folk_tag.get("original_text"),
        "original_schema": "folk",
        "offsets": folk_tag.get("offsets"),
    }
    return DATA(**kwargs)  # type: ignore[arg-type]


def convert_data_tag_to_data_object(tag_value: DataTag, schema: DataTagSchema) -> DATA:
    """
    Convert a DataTag dict to a DATA object.

    Args:
        tag_value (DataTag): The PEP350Tag to convert.
        schema (DataTagSchema): Schema for DataTag
    """
    # default fields should have already been promoted to data_fields by now.
    kwargs = upgrade_to_specific_schema(tag_value, schema)

    return DATA(**kwargs)  # type: ignore[arg-type]


def upgrade_to_specific_schema(tag_value: DataTag, schema: DataTagSchema, flat: bool = True) -> dict[str, Any]:
    """Convert a DataTag to a specific schema.

    Args:
        tag_value (DataTag): The DataTag to convert.
        schema (DataTagSchema): The schema to use for the conversion.
        flat (bool): If True, return a flat dict, otherwise return a nested dict.

    Returns:
        dict[str, Any]: A dictionary representation of the DataTag with fields promoted according to the schema.
    """
    data_fields = tag_value["fields"]["data_fields"]
    custom_fields = tag_value["fields"]["custom_fields"]
    final_data = {}
    final_custom = {}
    for found, value in data_fields.items():
        if found in schema["data_fields"]:
            final_data[found] = value
        else:
            final_custom[found] = value
    for found, value in custom_fields.items():
        if found in schema["data_fields"]:
            if found in final_data:
                logger.warning("Found same field in both data and custom")
            final_data[found] = value
        else:
            if found in final_custom:
                logger.warning("Found same field in both data and custom")
            final_custom[found] = value
    kwargs: DataTag | dict[str, Any] = {
        "code_tag": tag_value["code_tag"],
        "comment": tag_value["comment"],
        # Source Mapping
        "file_path": tag_value.get("file_path"),
        "line_number": tag_value.get("line_number"),
        "original_text": tag_value.get("original_text"),
        "original_schema": "pep350",
        "offsets": tag_value.get("offsets"),
    }
    if flat:
        kwargs["default_fields"] = tag_value["fields"]["default_fields"]  # type:ignore[typeddict-unknown-key]
        kwargs["data_fields"] = final_data  # type:ignore[typeddict-unknown-key]
        kwargs["custom_fields"] = final_custom  # type:ignore[typeddict-unknown-key]
        ud = tag_value["fields"]["unprocessed_defaults"]
        kwargs["unprocessed_defaults"] = ud  # type:ignore[typeddict-unknown-key]
        # kwargs["identity_fields"]=tag_value["fields"].get("identity_fields", {})  # type:ignore[typeddict-unknown-key]
    else:
        kwargs["fields"] = {
            "data_fields": final_data,
            "custom_fields": final_custom,
            "default_fields": tag_value["fields"]["default_fields"],
            "unprocessed_defaults": tag_value["fields"]["unprocessed_defaults"],
            "identity_fields": tag_value["fields"].get("identity_fields", []),
        }
        promote_fields(kwargs, schema)  # type: ignore[arg-type]
    return kwargs  # type: ignore[return-value]
