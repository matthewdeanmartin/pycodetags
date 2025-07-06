"""
TypedDict and methods for datas structure to represent folk tags
"""

from __future__ import annotations

try:
    from typing import Literal, TypedDict  # type: ignore[assignment,unused-ignore]
except ImportError:
    from typing_extensions import Literal  # type: ignore[assignment,unused-ignore] # noqa
    from typing_extensions import TypedDict  # noqa


DefaultFieldMeaning = Literal[
    "person",  # accurate because who knows what that name in parens means
    "assignee",
    "originator",  # compatible with pep350
    "tracker",
]


class FolkTag(TypedDict, total=False):
    """Represents a folk tag found in source code."""

    # data
    code_tag: str
    comment: str
    default_field: str | None
    custom_fields: dict[str, str]

    # data
    file_path: str
    offsets: tuple[int, int, int, int] | None
    original_text: str

    # domain specific
    tracker: str
    assignee: str
    originator: str
    person: str


def folk_tag_to_comment(tag: FolkTag) -> str:
    """Convert a FolkTag to a comment string."""
    people_text = ""
    custom_field_text = ""
    if tag.get("assignee") or tag.get("originator"):
        people = ",".join(_ for _ in (tag.get("assignee", ""), tag.get("originator", "")) if _)
        people.strip(", ")
        if people:
            people_text = f"({people.strip()})"
    if tag["custom_fields"]:

        for key, value in tag["custom_fields"].items():
            custom_field_text += f"{key}={value.strip()} "
        custom_field_text = f"({custom_field_text.strip()}) "

    return f"# {tag['code_tag'].upper()}{people_text}: {custom_field_text}{tag['comment'].strip()}".strip()
