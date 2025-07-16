"""
A TDG tag has fields on second line, comment is an issue title
and the third lines onward are issue body.

# TODO: This is title of the issue to create
# category=SomeCategory issue=123 estimate=30m author=alias
# This is a multiline description of the issue
# that will be in the "Body" property of the comment

"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Generator

from pycodetags.data_tags.data_tags_methods import DataTag
from pycodetags.data_tags.data_tags_parsers import parse_fields
from pycodetags.data_tags.data_tags_schema import DataTagSchema


def iterate_comments(
    source: str, source_file: Path | None, schemas: list[DataTagSchema]
) -> Generator[DataTag]:
    """
    Collect TDG style code tags from a given file.

    Args:
        source (str): The source text to process.
        source_file (Path | None): Where did the source come from.
        schemas (list[DataTagSchema]): Schemas that will be detected in file.

    Yields:
        DataTag: A generator yielding TDG style code tags found in the file.
    """
    # This regex is designed to find TDG-style comments.
    # It looks for a tag and title, a line of fields, and an optional multi-line body.
    # It must match from the beginning of a line.
    tdg_regex = re.compile(
        r"""
        ^[ \t]*#\s*(?P<code_tag>[A-Z]+):\s*(?P<comment>.*) # Line 1: Tag and Title
        \n[ \t]*#\s*(?P<field_string>[^\n]*)              # Line 2: Fields
        (?P<body_lines>(?:\n[ \t]*#\s*.*)*)                # Line 3+: Optional body
        """,
        re.MULTILINE | re.VERBOSE,
    )

    for match in tdg_regex.finditer(source):
        code_tag = match.group("code_tag").strip()
        comment = match.group("comment").strip()
        field_string = match.group("field_string").strip()
        body_lines_raw = match.group("body_lines")

        # Find the schema that matches the code_tag
        active_schema = None
        for schema in schemas:
            if code_tag in schema.get("matching_tags", []):
                active_schema = schema
                break

        if not active_schema:
            continue  # Skip if no schema matches the tag

        # Parse the fields using the existing parser from the library
        fields = parse_fields(field_string, active_schema, strict=False)

        # Process the body, cleaning each line
        if body_lines_raw:
            cleaned_body_lines = []
            for line in body_lines_raw.strip().split("\n"):
                # Remove leading '#' and optional whitespace
                cleaned_line = re.sub(r"^[ \t]*#\s?", "", line)
                cleaned_body_lines.append(cleaned_line)
            body = "\n".join(cleaned_body_lines)

            if body:
                fields["custom_fields"]["body"] = body

        # Calculate offsets by converting character offsets to line and column numbers
        start_char_offset = match.start()
        end_char_offset = match.end()

        start_line = source.count("\n", 0, start_char_offset)
        start_col = start_char_offset - source.rfind("\n", 0, start_char_offset) - 1
        end_line = source.count("\n", 0, end_char_offset)
        end_col = end_char_offset - source.rfind("\n", 0, end_char_offset) - 1

        # Construct the DataTag object
        data_tag: DataTag = {
            "code_tag": code_tag,
            "comment": comment,
            "fields": fields,
            "file_path": str(source_file) if source_file else None,
            "original_text": match.group(0),
            "original_schema": "TDG",
            "offsets": (start_line, start_col, end_line, end_col),
        }

        yield data_tag
