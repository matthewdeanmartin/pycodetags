"""Locate Python comments using tokenizer character positions, never text matching."""

from __future__ import annotations

import io
import logging
import tokenize
from functools import lru_cache

from pycodetags.exceptions import FileParsingError

logger = logging.getLogger(__name__)

__all__ = ["find_comment_blocks_from_string", "find_comment_blocks_from_string_fallback"]


def extract_comment_lines(lines: list[str], offsets: tuple[int, int, int, int]) -> str:
    """Slice already-split source lines, retaining internal line endings and indentation."""
    start_line, start_char, end_line, end_char = offsets
    if start_line == end_line:
        return lines[start_line][start_char:end_char]
    return lines[start_line][start_char:] + "".join(lines[start_line + 1 : end_line]) + lines[end_line][:end_char]


@lru_cache(maxsize=32)
def scan_comment_blocks(source: str) -> tuple[tuple[int, int, int, int, str], ...]:
    """Find comment blocks in source order with zero-based character offsets.

    Only adjacent comment-only lines extend a block. An inline comment starts its own block so
    intervening executable code can never become part of a tag's source span. Tokenization failures
    raise FileParsingError. A bounded process-local cache avoids disk serialization.
    """
    lines = io.StringIO(source).readlines()
    spans: list[tuple[int, int, int, int]] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type != tokenize.COMMENT:
                continue
            start_line, start_char = token.start
            end_line, end_char = token.end
            start_line -= 1
            end_line -= 1
            if spans and start_line == spans[-1][2] + 1 and not lines[start_line][:start_char].strip():
                block_start_line, block_start_char = spans[-1][:2]
                spans[-1] = (block_start_line, block_start_char, end_line, end_char)
            else:
                spans.append((start_line, start_char, end_line, end_char))
    except (tokenize.TokenError, SyntaxError, ValueError) as error:
        raise FileParsingError("Cannot tokenize Python source; no scan results committed.") from error
    return tuple((*span, extract_comment_lines(lines, span)) for span in spans)


def find_comment_blocks_from_string(source: str) -> list[tuple[int, int, int, int, str]]:
    """Return comment blocks and their exact source spans, with cached tokenization."""
    return list(scan_comment_blocks(source))


def extract_comment_text(text: str, offsets: tuple[int, int, int, int]) -> str:
    """Extract the exact source slice at zero-based line/character offsets."""
    return extract_comment_lines(io.StringIO(text).readlines(), offsets)


def find_comment_blocks_from_string_fallback(source: str) -> list[tuple[int, int, int, int, str]]:
    """Use the same tokenizer for callers of the former fallback entry point."""
    return list(scan_comment_blocks(source))
