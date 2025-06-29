"""
Given data structure returned by collect submodule, creates human-readable reports.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pycodetags.data_tag_types import DATA
from pycodetags.view_tools import group_and_sort

logger = logging.getLogger(__name__)


def print_validate(found: list[DATA]) -> None:
    """
    Prints validation errors for TODOs.

    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    for item in sorted(found, key=lambda x: x.code_tag or ""):
        validations = item.validate()
        if validations:
            print(item.as_data_comment())
            for validation in validations:
                print(f"  {validation}")
            print()


def print_html(found: list[DATA]) -> None:
    """
    Prints TODOs and Dones in a structured HTML format.

    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    tags = set()
    for todo in found:
        tags.add(todo.code_tag)

    for tag in tags:
        for todo in found:
            # TODO: find more efficient way to filter.
            if todo.code_tag == tag:
                print(f"<h1>{tag}</h1>")
                print("<ul>")
                print(f"<li><strong>{todo.comment}</strong><br>{todo.data_fields}</li>")
                print("</ul>")


def print_text(found: list[DATA]) -> None:
    """
    Prints TODOs and Dones in text format.
    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    todos = found
    if todos:
        grouped = group_and_sort(
            todos, key_fn=lambda x: x.code_tag or "N/A", sort_items=True, sort_key=lambda x: x.comment or "N/A"
        )
        for tag, items in grouped.items():
            print(f"--- {tag.upper()} ---")
            for todo in items:
                print(todo.as_pep350_comment())
                print()
    else:
        print("No Code Tags found.")


def print_json(found: list[DATA]) -> None:
    """
    Prints TODOs and Dones in a structured JSON format.
    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    todos = found

    output = [t.to_dict() for t in todos]

    def default(o: Any) -> str:
        if hasattr(o, "todo_meta"):
            o.todo_meta = None

        return json.dumps(o.to_dict()) if hasattr(o, "to_dict") else str(o)

    print(json.dumps(output, indent=2, default=default))


def print_data_md(found: list[DATA]) -> None:
    """
    Outputs DATA items in a markdown format.

    """
    # config = get_code_tags_config()

    print(found)
