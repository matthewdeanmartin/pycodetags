# This test code was written by the `hypothesis.extra.ghostwriter` module
# and is provided under the Creative Commons Zero public domain dedication.

from hypothesis import given
from hypothesis import strategies as st

import pycodetags.comment_finder


@given(source=st.text())
def test_fuzz_find_comment_blocks_from_string(source: str) -> None:
    pycodetags.comment_finder.find_comment_blocks_from_string(source=source)


@given(source=st.text())
def test_fuzz_find_comment_blocks_from_string_fallback(source: str) -> None:
    pycodetags.comment_finder.find_comment_blocks_from_string_fallback(source=source)
