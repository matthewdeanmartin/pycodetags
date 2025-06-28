"""
Find and parse PEP-350 style code tags.

Examples:
List value in a default field.
# FIXME: Seems like this Loop should be finite. <MDE, CLE d:2015-1-1 p:2>

After code, field aliases, default fields
while True: # BUG: Crashes if run on Sundays. <MDE 2005-09-04 d:2015-6-6 p:2>

Multiline, mixed key-value separators
# TODO: This is a complex task that needs more details.
# <
#   assignee=JRNewbie
#   priority:3
#   due=2025-12-25
#   custom_field: some_value
# >

A default field with explicit key
# RFE: Add a new feature for exporting. <assignee:Micahe,CLE priority=1 2025-06-15>

"""

from __future__ import annotations

import logging
import tokenize
from collections.abc import Generator
from pathlib import Path

from pycodetags.comment_finder import find_comment_blocks
from pycodetags.data_tags import DataTag, parse_codetags
from pycodetags.specific_schemas import PEP350Schema

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict # noqa

logger = logging.getLogger(__name__)


class Fields(TypedDict, total=False):
    """Fields extracted from PEP-350 style code tags."""

    # HACK: maybe make these always a list?
    assignee: str  # make this go away and always promote to assignee, isomorphic with custom_tags?
    assignees: list[str]

    # Best identity fields, when they exist!
    originator: str
    origination_date: str

    # Metadata, shouldn't be set by user.
    _file_path: str  # mutable across time, identity for same revision
    _line_number: str  # mutable across time, identity for same revision
    _file_revision: str  # With file_path, line_number, forms identity

    # When all of these mutable fields, or almost all of these are they same, the object probably points
    # to the same real world entity.
    # creates need for promotion
    custom_fields: dict[str, str]  # mutable
    priority: str  # mutable
    due: str  # mutable
    tracker: str  # mutable
    status: str  # mutable
    category: str  # mutable
    iteration: str  # mutable
    release: str  # mutable

    # creates need for alias merging, when both priority and p exist
    p: str
    d: str
    t: str
    s: str
    c: str
    i: str
    r: str
    a: str


field_aliases: dict[str, str] = {
    "p": "priority",
    "d": "due",
    "t": "tracker",
    "s": "status",
    "c": "category",
    "i": "iteration",
    "r": "release",
    "a": "assignee",
    "priority": "priority",
    "due": "due",
    "tracker": "tracker",
    "status": "status",
    "category": "category",
    "iteration": "iteration",
    "release": "release",
    "assignee": "assignee",
    "originator": "originator",
}


def extract_comment_blocks_fallback(filename: str) -> list[list[str]]:
    """
    Dead code, useful if comment-ast isn't avail

    Extract comment blocks from a Python file, grouping consecutive comments together.

    Args:
        filename (str): The path to the Python file to extract comments from.

    Returns:
        list[list[str]]: A list of lists, where each inner list contains consecutive comment lines.
    """
    comment_blocks = []
    current_block = []
    last_comment_lineno = -2

    with open(filename, "rb") as f:
        tokens = list(tokenize.tokenize(f.readline))

    for token in tokens:
        if token.type == tokenize.COMMENT:
            lineno = token.start[0]
            comment_text = token.string.strip()

            # Group consecutive comment lines
            if lineno == last_comment_lineno + 1:
                current_block.append(comment_text)
            else:
                # Start a new block if the current line is not consecutive
                if current_block:
                    comment_blocks.append(current_block)
                current_block = [comment_text]

            last_comment_lineno = lineno

        # If a non-comment, non-whitespace token is encountered, it breaks a comment block
        elif token.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.ENCODING, tokenize.INDENT, tokenize.DEDENT):
            if token.start[0] > last_comment_lineno + 1:  # Check if there's a gap
                if current_block:
                    comment_blocks.append(current_block)
                    current_block = []
                last_comment_lineno = -2  # Reset to indicate no recent comment

    # Add any remaining current block at the end of the file
    if current_block:
        comment_blocks.append(current_block)

    return comment_blocks


def collect_pep350_code_tags(file: str) -> Generator[DataTag]:
    """
    Collect PEP-350 style code tags from a given file.

    Args:
        file (str): The path to the file to process.

    Yields:
        PEP350Tag: A generator yielding PEP-350 style code tags found in the file.
    """
    logger.info(f"collect_pep350_code_tags: processing {file}")
    things = []
    for _start_line, _start_char, _end_line, _end_char, final_comment in find_comment_blocks(Path(file)):
        # Can only be one comment block now!
        thing = parse_codetags(final_comment, PEP350Schema, strict=False)
        things.extend(thing)
    yield from things
