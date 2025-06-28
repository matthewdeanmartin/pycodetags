import pytest

from pycodetags.comment_finder import find_comment_blocks_fallback


def test_missing_file(tmp_path):
    non_existing = tmp_path / "nofile.py"
    with pytest.raises(FileNotFoundError):
        list(find_comment_blocks_fallback(non_existing))


def test_wrong_extension(tmp_path):
    txt = tmp_path / "not_python.txt"
    txt.write_text("foo = 1")
    with pytest.raises(ValueError):
        list(find_comment_blocks_fallback(txt))


def test_no_comments(tmp_path):
    p = tmp_path / "clean.py"
    p.write_text("def foo():\n    return 42\n")
    assert not list(find_comment_blocks_fallback(p))


def test_single_comment_line(tmp_path):
    p = tmp_path / "single.py"
    p.write_text("# hello world\n")
    blocks = list(find_comment_blocks_fallback(p))
    assert blocks == [(0, 0, 0, len("# hello world"), "# hello world")]


def test_contiguous_comment_block(tmp_path):
    p = tmp_path / "block.py"
    content = "# one\n# two\n# three\n"
    p.write_text(content)
    blocks = list(find_comment_blocks_fallback(p))
    assert len(blocks) == 1
    start, sc, end, ec, text = blocks[0]
    assert (start, sc) == (0, 0)
    assert (end, ec) == (2, len("# three"))
    assert text == "# one\n# two\n# three"


def test_multiple_blocks(tmp_path):
    p = tmp_path / "multi.py"
    lines = ["# first\n", "print()\n", "# second line 1\n", "# second line 2\n", "x = 2\n", "# third\n"]
    p.write_text("".join(lines))
    blocks = list(find_comment_blocks_fallback(p))
    assert len(blocks) == 3

    # first block
    b1 = blocks[0]
    assert b1 == (0, 0, 0, len("# first"), "# first")
    # second block
    b2 = blocks[1]
    assert b2 == (2, 0, 3, len("# second line 2"), "# second line 1\n# second line 2")
    # third block
    b3 = blocks[2]
    assert b3 == (5, 0, 5, len("# third"), "# third")


def test_inline_comments(tmp_path):
    p = tmp_path / "inline.py"
    p.write_text("x = 1  # comment here\n\ny = 2  # another\nz = 3\n")
    blocks = list(find_comment_blocks_fallback(p))
    # Two inline comments produce two blocks
    assert len(blocks) == 2
    # Check second inline comment
    _, _, _, _, text2 = blocks[1]
    assert text2 == "# another"


def test_block_at_end_of_file(tmp_path):
    p = tmp_path / "endblock.py"
    p.write_text("foo = 1\n# at end\n# still end")
    blocks = list(find_comment_blocks_fallback(p))
    assert len(blocks) == 1
    start, _, end, _, text = blocks[0]
    assert start == 1
    assert end == 2
    assert text == "# at end\n# still end"
