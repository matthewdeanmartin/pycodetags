"""Arbitrary text either has exact comment spans or produces a declared parse failure."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pycodetags.exceptions import FileParsingError
from pycodetags.python.comment_finder import (
    extract_comment_text,
    find_comment_blocks_from_string,
    find_comment_blocks_from_string_fallback,
)


@pytest.mark.parametrize("finder", [find_comment_blocks_from_string, find_comment_blocks_from_string_fallback])
@given(source=st.text())
def test_arbitrary_text_has_exact_spans_or_explicit_failure(finder, source):
    try:
        blocks = finder(source)
    except FileParsingError:
        return
    for first, column, last, end, text in blocks:
        assert text.startswith("#")
        assert extract_comment_text(source, (first, column, last, end)) == text
