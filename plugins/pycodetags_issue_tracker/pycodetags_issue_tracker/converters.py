"""
Converters for FolkTag and PEP350Tag to TODO
"""

from __future__ import annotations

import logging

from pycodetags_issue_tracker.todo_object_schema import TODO_KEYWORDS
from pycodetags_issue_tracker.todo_tag_types import TODO

from pycodetags.data_tags import DataTag
from pycodetags.folk_code_tags import FolkTag

logger = logging.getLogger(__name__)


def blank_to_null(value: str | None) -> str | None:
    """
    Convert a blank string to None.

    Args:
        value (str | None): The value to convert.

    Returns:
        str | None: The converted value.
    """
    if isinstance(value, list):
        return [_.strip() for _ in value]
    if value is None or value.strip() == "":
        return None
    return value.strip()


def convert_folk_tag_to_TODO(folk_tag: FolkTag) -> TODO:
    """
    Convert a FolkTag to a TODO object.

    Args:
        folk_tag (FolkTag): The FolkTag to convert.
    """
    kwargs = {
        "code_tag": folk_tag.get("code_tag"),
        "_file_path": folk_tag.get("file_path"),
        "_line_number": folk_tag.get("line_number"),
        # folk_tag.get("default_field"),
        "custom_fields": folk_tag.get("custom_fields"),
        "comment": folk_tag["comment"],  # required
        "tracker": folk_tag.get("tracker"),
        "assignee": blank_to_null(folk_tag.get("assignee")),
        "originator": blank_to_null(folk_tag.get("originator")),
        # person=folk_tag.get("person")
        "_original_text": folk_tag.get("original_text"),
        "_original_schema": "folk",
    }
    custom_fields = folk_tag.get("custom_fields", {})
    for keyword in TODO_KEYWORDS:
        for field_key, field_value in custom_fields.items():
            # Promote custom fields to kwargs if they match the keyword
            # and the keyword is not already in kwargs
            if keyword == field_key and keyword not in kwargs:
                kwargs[keyword] = field_value
            if keyword == field_key and keyword not in kwargs:
                logger.warning("Duplicate keyword found in custom fields: %s", keyword)
    return TODO(**kwargs)  # type: ignore[arg-type]


def convert_pep350_tag_to_TODO(pep350_tag: DataTag) -> TODO:
    """
    Convert a PEP350Tag to a TODO object.

    Args:
        pep350_tag (PEP350Tag): The PEP350Tag to convert.
    """
    # default fields should have already been promoted to data_fields by now.
    data_fields = pep350_tag["fields"]["data_fields"]
    custom_fields = pep350_tag["fields"]["custom_fields"]
    kwargs = {
        "code_tag": pep350_tag["code_tag"],
        "comment": pep350_tag["comment"],
        "custom_fields": custom_fields,
        # specific fields
        "assignee": blank_to_null(data_fields.get("assignee")),
        "originator": blank_to_null(data_fields.get("originator")),
        # due dates
        "due": data_fields.get("due"),
        "iteration": data_fields.get("iteration"),
        "release": data_fields.get("release"),
        # integrations
        "tracker": data_fields.get("tracker"),
        # idiosyncratic
        "priority": data_fields.get("priority"),
        "status": data_fields.get("status"),
        "category": data_fields.get("category"),
        # Source Mapping
        "_file_path": data_fields.get("_file_path"),
        "_line_number": data_fields.get("_line_number"),
        "_original_text": pep350_tag.get("original_text"),
        "_original_schema": "pep350",
    }

    custom_fields = pep350_tag["fields"].get("custom_fields", {})
    for keyword in TODO_KEYWORDS:
        for field_key, field_value in custom_fields.items():
            # Promote custom fields to kwargs if they match the keyword
            # and the keyword is not already in kwargs
            if keyword == field_key and keyword not in kwargs:
                kwargs[keyword] = field_value
            if keyword == field_key and keyword not in kwargs:
                logger.warning("Duplicate keyword found in custom fields: %s", keyword)

    return TODO(**kwargs)  # type: ignore[arg-type]
