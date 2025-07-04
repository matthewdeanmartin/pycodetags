"""
Finds comments using the AST parser.

If we look for comments with regex, we risk finding comments inside of structure that are not comments.

For older versions of python, the code falls back to string parsing instead of AST parsing.

Once a comment block is found, it could still have multiple code tags in it.
"""

from __future__ import annotations

import logging
from ast import walk
from collections.abc import Generator
from pathlib import Path
from typing import Any

from pycodetags.exceptions import FileParsingError

try:
    from ast_comments import Comment, parse
except ImportError:
    Comment: Any = None  # type: ignore[no-redef]
    parse: Any = None  # type: ignore[no-redef]

LOGGER = logging.getLogger(__name__)


def find_comment_blocks(path: Path) -> Generator[tuple[int, int, int, int, str], None, None]:
    """Parses a Python source file and yields comment block ranges.

    Uses `ast-comments` to locate all comments, and determines the exact offsets
    for each block of contiguous comments.

    Args:
        path (Path): Path to the Python source file.

    Yields:
        Tuple[int, int, int, int, str]: (start_line, start_char, end_line, end_char, comment)
        representing the comment block's position in the file (0-based).
    """
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix != ".py":
        raise FileParsingError(f"Expected a Python file (.py), got: {path.suffix}")

    source = path.read_text(encoding="utf-8")
    return find_comment_blocks_from_string(source)


def find_comment_blocks_from_string(source: str) -> Generator[tuple[int, int, int, int, str], None, None]:
    """Parses a Python source file and yields comment block ranges.

    Uses `ast-comments` to locate all comments, and determines the exact offsets
    for each block of contiguous comments.

    Args:
        source (str): Python source text.

    Yields:
        Tuple[int, int, int, int, str]: (start_line, start_char, end_line, end_char, comment)
        representing the comment block's position in the file (0-based).
    """
    if parse is None:
        # Hack for 3.7!
        yield from find_comment_blocks_fallback(source)
        return
        # type: ignore[no-redef,unused-ignore]
    tree = parse(source)
    lines = source.splitlines()

    # Filter out comment nodes
    # BUG, fails to walk the whole tree. This is shallow.
    comments = [node for node in walk(tree) if isinstance(node, Comment)]

    def comment_pos(comment: Comment) -> tuple[int, int, int, int]:
        """Get the position of a comment as (start_line, start_char, end_line, end_char)."""
        for i, line in enumerate(lines):
            idx = line.find(comment.value)
            if idx != -1:
                return (i, idx, i, idx + len(comment.value))
        raise FileParsingError(f"Could not locate comment in source: {comment.value}")

    # Group comments into blocks
    block: list[tuple[int, int, int, int]] = []

    for comment in comments:
        pos = comment_pos(comment)

        if not block:
            block.append(pos)
        else:
            prev_end_line = block[-1][2]
            if pos[0] == prev_end_line + 1:
                # Consecutive line: extend block
                block.append(pos)
            else:
                # Yield previous block
                start_line, start_char, _, _ = block[0]
                end_line, _, _, end_char = block[-1]
                final_comment = extract_comment_text(source, (start_line, start_char, end_line, end_char))
                yield (start_line, start_char, end_line, end_char, final_comment)
                block = [pos]

    if block:
        start_line, start_char, _, _ = block[0]
        end_line, _, _, end_char = block[-1]
        final_comment = extract_comment_text(source, (start_line, start_char, end_line, end_char))
        yield (start_line, start_char, end_line, end_char, final_comment)


def extract_comment_text_from_file(path: Path, offsets: tuple[int, int, int, int]) -> str:
    return extract_comment_text(path.read_text(encoding="utf-8"), offsets)


def extract_comment_text(text: str, offsets: tuple[int, int, int, int]) -> str:
    """Extract the comment text from a file given start/end line/char offsets.

    Args:
        text (str): text of source code
        offsets (tuple): A tuple of (start_line, start_char, end_line, end_char),
            all 0-based.

    Returns:
        str: The exact substring from the file containing the comment block.
    """
    start_line, start_char, end_line, end_char = offsets

    lines = text.splitlines()

    if start_line == end_line:
        return lines[start_line][start_char:end_char]

    # Multi-line block
    block_lines = [lines[start_line][start_char:]]
    for line_num in range(start_line + 1, end_line):
        block_lines.append(lines[line_num])
    block_lines.append(lines[end_line][:end_char])

    return "\n".join(block_lines)


def find_comment_blocks_fallback(path: Path | str) -> Generator[tuple[int, int, int, int, str], None, None]:
    """Parse a Python file and yield comment block positions and content.

    Args:
        path (Path): Path to the Python source file.

    Yields:
        Tuple[int, int, int, int, str]: A tuple of (start_line, start_char, end_line, end_char, comment)
        representing the block's location and the combined comment text. All indices are 0-based.
    """
    if isinstance(path, Path):
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        if path.suffix != ".py":
            raise FileParsingError(f"Expected a Python file (.py), got: {path.suffix}")

        LOGGER.info("Reading Python file: %s", path)

        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = path.split("\n")

    in_block = False
    start_line = start_char = 0
    end_line = end_char = 0
    comment_lines: list[str] = []

    for idx, line in enumerate(lines):
        line_wo_newline = line.rstrip("\n")
        comment_pos = line.find("#")

        if comment_pos != -1:
            if not in_block:
                # Start a new block
                in_block = True
                start_line = idx
                start_char = comment_pos
                comment_lines = []
                LOGGER.debug("Starting comment block at line %d, char %d", start_line, start_char)

            end_line = idx
            end_char = len(line_wo_newline)
            comment_lines.append(line_wo_newline[comment_pos:])

            # Check if next line is non-comment or this is a standalone inline comment
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            next_comment_pos = next_line.find("#")
            next_stripped = next_line.strip()

            if not next_stripped or next_comment_pos == -1:
                # End of comment block
                comment_text = "\n".join(comment_lines)
                LOGGER.debug("Ending comment block at line %d, char %d", end_line, end_char)
                yield (start_line, start_char, end_line, end_char, comment_text)
                in_block = False

        else:
            if in_block:
                # Previous line had comment, current one doesn't: close block
                comment_text = "\n".join(comment_lines)
                LOGGER.debug("Ending comment block at line %d, char %d", end_line, end_char)
                yield (start_line, start_char, end_line, end_char, comment_text)
                in_block = False

    if in_block:
        comment_text = "\n".join(comment_lines)
        LOGGER.debug("Ending final comment block at line %d, char %d", end_line, end_char)
        yield (start_line, start_char, end_line, end_char, comment_text)


if parse is None:
    # Hack for 3.7!
    find_comment_blocks = find_comment_blocks_fallback  # type: ignore[no-redef,unused-ignore]
