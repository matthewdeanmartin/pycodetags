"""
Converters for FolkTag and PEP350Tag to TODO
"""

from __future__ import annotations

import logging

from pycodetags.data_tag_types import DATA
from pycodetags.data_tags import DataTag, DataTagSchema
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
        "_file_path": folk_tag.get("file_path"),
        "_line_number": folk_tag.get("line_number"),
        "_original_text": folk_tag.get("original_text"),
        "_original_schema": "folk",
        "_offsets": folk_tag.get("offsets"),
    }
    return DATA(**kwargs)  # type: ignore[arg-type]


def convert_pep350_tag_to_DATA(pep350_tag: DataTag, schema: DataTagSchema) -> DATA:
    """
    Convert a PEP350Tag to a DATA object.

    Args:
        pep350_tag (PEP350Tag): The PEP350Tag to convert.
        schema (DataTagSchema): Schema for DataTag
    """
    # default fields should have already been promoted to data_fields by now.
    data_fields = pep350_tag["fields"]["data_fields"]
    custom_fields = pep350_tag["fields"]["custom_fields"]

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

    kwargs = {
        "code_tag": pep350_tag["code_tag"],
        "comment": pep350_tag["comment"],
        "data_fields": final_data,
        "custom_fields": final_custom,
        # Source Mapping
        "_file_path": pep350_tag.get("file_path"),
        "_line_number": pep350_tag.get("line_number"),
        "_original_text": pep350_tag.get("original_text"),
        "_original_schema": "pep350",
        "_offsets": pep350_tag.get("offsets"),
    }
    return DATA(**kwargs)  # type: ignore[arg-type]
