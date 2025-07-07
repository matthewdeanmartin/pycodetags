"""
Finds all folk schema tags in source files.

Folk tags roughly follow

# TODO: comment
# TODO(user): comment
# TODO(ticket): comment
# TODO(default_field): Message with domain.com/ticket-123

Optionally

# TODO: Multiline
# comment

Valid tags lists are important for doing looser parsing, e.g. omitting colon, multiline, lowercase etc.

Not sure if I will implement completely loose parsing.
"""

from __future__ import annotations

import logging
import re

from pycodetags.folk_tags.folk_tags_schema import DefaultFieldMeaning, FolkTag

try:
    from typing import Literal, TypedDict  # type: ignore[assignment,unused-ignore]
except ImportError:
    from typing_extensions import Literal  # type: ignore[assignment,unused-ignore] # noqa
    from typing_extensions import TypedDict  # noqa

__all__ = ["process_text"]

logger = logging.getLogger(__name__)


# def find_source_tags(
#     source_path: str,
#     valid_tags: list[str] | None = None,
#     allow_multiline: bool = False,
#     default_field_meaning: DefaultFieldMeaning = "assignee",
# ) -> list[FolkTag]:
#     """
#     Finds all folk tags in the source files.
#
#     Args:
#         source_path (str): Path to the source file or directory.
#         valid_tags (list[str], optional): List of valid code tags to look for. If None, all tags are considered valid.
#         allow_multiline (bool, optional): Whether to allow multiline comments. Defaults to False.
#         default_field_meaning (DefaultFieldMeaning, optional): Meaning of the default field. Defaults to "assignee".
#
#     Returns:
#         list[FolkTag]: A list of FolkTag dictionaries found in the source files.
#     """
#     if allow_multiline and not valid_tags:
#         raise SchemaError("Must include valid tag list if you want to allow multiline comments")
#
#     if not valid_tags:
#         valid_tags = []
#
#     if not os.path.exists(source_path):
#         raise FileNotFoundError(f"The path '{source_path}' does not exist.")
#
#     if os.path.isfile(source_path):
#         files_to_scan = [source_path]
#     else:
#         files_to_scan = []
#         for root, _, files in os.walk(source_path):
#             for file in files:
#                 files_to_scan.append(os.path.join(root, file))
#
#     found_tags: list[FolkTag] = []
#     for file_path in files_to_scan:
#         with open(file_path, encoding="utf-8", errors="ignore") as f:
#             text = f.read()
#
#             process_text(text, allow_multiline, default_field_meaning, found_tags, file_path, valid_tags)
#
#     return found_tags
#
#
# def process_text(
#     text: str,
#     allow_multiline: bool,
#     default_field_meaning: DefaultFieldMeaning,
#     found_tags: list[FolkTag],
#     file_path: str,
#     valid_tags: list[str],
# ) -> None:
#     if "\r\n" in text:
#         lines = text.split("\r\n")
#     else:
#         lines = text.split("\n")
#
#     if len(lines) == 1:
#         logger.debug(f"Processing  {file_path}: {lines[0]}")
#     else:
#         for line in lines:
#             logger.debug(f"Processing {file_path} ==>: {line}")
#     idx = 0
#     while idx < len(lines):
#         consumed = process_line(
#             file_path,
#             found_tags,
#             lines,
#             idx,
#             # schema
#             valid_tags,
#             allow_multiline,
#             default_field_meaning,
#         )
#         idx += consumed


def extract_first_url(text: str) -> str | None:
    """
    Extracts the first URL from a given text.

    Args:
        text (str): The text to search for URLs.

    Returns:
        str | None: The first URL found in the text, or None if no URL is found.
    """
    # Regex pattern to match URLs with or without scheme
    pattern = r"(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/[^\s]+)"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def process_text(
    text: str,
    allow_multiline: bool,
    default_field_meaning: DefaultFieldMeaning,
    found_tags: list[FolkTag],
    file_path: str,
    valid_tags: list[str],
) -> None:
    if "\r\n" in text:
        lines = text.split("\r\n")
    else:
        lines = text.split("\n")

    if len(lines) == 1:
        logger.debug(f"Processing  {file_path}: {lines[0]}")
    else:
        for log_line in lines:
            logger.debug(f"Processing {file_path} ==>: {log_line}")

    line_index = 0
    while line_index < len(lines):
        consumed_lines = process_line(
            file_path,
            found_tags,
            lines,
            line_index,
            valid_tags,
            allow_multiline,
            default_field_meaning,
        )
        line_index += consumed_lines


def process_line(
    file_path: str,
    found_tags: list[FolkTag],
    lines: list[str],
    start_idx: int,
    valid_tags: list[str],
    allow_multiline: bool,
    default_field_meaning: DefaultFieldMeaning,
) -> int:
    current_line = lines[start_idx]

    match = re.match(r"\s*#\s*([A-Z]+)\b(.*)", current_line)
    if not match:
        return 1

    code_tag_candidate = match.group(1)
    content = match.group(2).strip()

    if valid_tags and code_tag_candidate not in valid_tags:
        return 1

    if content.startswith(":"):
        content = content[1:].lstrip()

    start_line = start_idx
    start_char = current_line.find("#")

    current_idx = start_idx
    if allow_multiline and valid_tags:
        multiline_content = [content]
        next_idx = current_idx + 1
        while next_idx < len(lines):
            next_line = lines[next_idx].strip()
            if next_line.startswith("#") and not any(re.match(rf"#\s*{t}\b", next_line) for t in valid_tags):
                multiline_content.append(next_line.lstrip("# "))
                next_idx += 1
            else:
                break
        content = " ".join(multiline_content)
        end_line = next_idx - 1
        end_char = len(lines[end_line].rstrip())
        consumed_lines = next_idx - start_idx
    else:
        end_line = start_idx
        end_char = len(current_line.rstrip())
        consumed_lines = 1

    default_field = None
    custom_fields = {}
    comment = content

    field_match = re.match(r"\(([^)]*)\):(.*)", content)
    if field_match:
        field_section = field_match.group(1).strip()
        comment = field_match.group(2).strip()

        for part in field_section.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                key, val = part.split("=", 1)
                custom_fields[key.strip()] = val.strip()
            else:
                if default_field is None:
                    default_field = part
                else:
                    default_field += ", " + part
    else:
        id_match = re.match(r"(\d+):(.*)", content)
        if id_match:
            default_field = id_match.group(1)
            comment = id_match.group(2).strip()

    found_tag: FolkTag = {
        "file_path": file_path,
        "code_tag": code_tag_candidate,
        "default_field": default_field,
        "custom_fields": custom_fields,
        "comment": comment,
        "original_text": content,
        "offsets": (start_line, start_char, end_line, end_char),
    }

    if default_field and default_field_meaning:
        found_tag[default_field_meaning] = default_field

    url = extract_first_url(comment)
    if url:
        found_tag["tracker"] = url

    if len(code_tag_candidate) > 1:
        found_tags.append(found_tag)

    return consumed_lines
