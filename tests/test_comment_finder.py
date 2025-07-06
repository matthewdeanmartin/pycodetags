import sys
from pathlib import Path

import pytest

from pycodetags.comment_finder import extract_comment_text, find_comment_blocks_from_string


def _write_temp_file(tmp_path: Path, content: str) -> Path:
    file_path = tmp_path / "example.py"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_single_comment_block():
    content = """\
print("hello")
# Start of a comment
# Comment block continues
print("no more comment block")
"""
    blocks = list(find_comment_blocks_from_string(content))
    assert blocks == [
        (
            1,
            0,
            2,
            25,
            """# Start of a comment
# Comment block continues""",
        )
    ]
    assert (
        extract_comment_text(content, (1, 0, 2, 25))
        == """# Start of a comment
# Comment block continues"""
    )


def test_three_comment_blocks():
    content = """\
print("hello")

# Start of a comment

print("again") # This is a comment block, a new one

# New and different comment block

print("no more comment block")
"""
    blocks = list(find_comment_blocks_from_string(content))
    assert blocks == [
        (2, 0, 2, 20, "# Start of a comment"),
        (4, 15, 4, 51, "# This is a comment block, a new one"),
        (6, 0, 6, 33, "# New and different comment block"),
    ]
    assert extract_comment_text(content, (2, 0, 2, 20)) == """# Start of a comment"""
    assert extract_comment_text(content, (4, 15, 4, 51)) == """# This is a comment block, a new one"""
    assert (
        extract_comment_text(
            content,
            (
                6,
                0,
                6,
                33,
            ),
        )
        == """# New and different comment block"""
    )


# @pytest.mark.skip("This is the degenerate case.")
@pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python > 3.7")
def test_no_comment_blocks():
    content = '''\
print("hello")

""" # Not a comment """

'# Also not a comment'

print("no more comment block")
'''
    blocks = list(find_comment_blocks_from_string(content))
    assert not blocks


def test_triple():
    content = """
# TODO: Finish this module <priority:high assignee:dev_a>
# A regular comment
# FIXME: Refactor this part <due:2025-06-30>
def some_function():
    # BUG: This might cause an error in production <status:open c:critical>
    pass
"""
    blocks = list(find_comment_blocks_from_string(content))
    assert len(blocks) == 2
