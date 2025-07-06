from pycodetags.comment_finder import find_comment_blocks_from_string_fallback


def test_single_comment_line():
    content = "# hello world\n"
    blocks = list(find_comment_blocks_from_string_fallback(content))
    assert blocks == [(0, 0, 0, len("# hello world"), "# hello world")]


def test_contiguous_comment_block():
    content = "# one\n# two\n# three\n"

    blocks = list(find_comment_blocks_from_string_fallback(content))
    assert len(blocks) == 1
    start, sc, end, ec, text = blocks[0]
    assert (start, sc) == (0, 0)
    assert (end, ec) == (2, len("# three"))
    assert text == "# one\n# two\n# three"


def test_multiple_blocks():

    lines = ["# first\n", "print()\n", "# second line 1\n", "# second line 2\n", "x = 2\n", "# third\n"]
    content = "".join(lines)
    blocks = list(find_comment_blocks_from_string_fallback(content))
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


def test_inline_comments():
    content = "x = 1  # comment here\n\ny = 2  # another\nz = 3\n"
    blocks = list(find_comment_blocks_from_string_fallback(content))
    # Two inline comments produce two blocks
    assert len(blocks) == 2
    # Check second inline comment
    _, _, _, _, text2 = blocks[1]
    assert text2 == "# another"


def test_block_at_end_of_file():

    p = "foo = 1\n# at end\n# still end"
    blocks = list(find_comment_blocks_from_string_fallback(p))
    assert len(blocks) == 1
    start, _, end, _, text = blocks[0]
    assert start == 1
    assert end == 2
    assert text == "# at end\n# still end"
