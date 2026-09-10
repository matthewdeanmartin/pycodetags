"""Source positions must address physical comments, independently of their text."""

from dataclasses import replace
from pathlib import Path

import pytest

from pycodetags.common_interfaces import string_to_data
from pycodetags.mutator import apply_mutations, delete_tags
from pycodetags.pure_data_schema import PureDataSchema
from pycodetags.python.comment_finder import extract_comment_text, find_comment_blocks_from_string


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_repeated_comments_have_distinct_exact_spans(newline):
    text = newline.join(['value = "# TODO: repeated"', "# TODO: repeated", "value = 1", "# TODO: repeated", ""])
    blocks = find_comment_blocks_from_string(text)
    assert [(block[0], block[2]) for block in blocks] == [(1, 1), (3, 3)]
    for block in blocks:
        assert extract_comment_text(text, block[:4]) == block[4] == "# TODO: repeated"


def test_nested_comments_are_returned_in_source_order():
    source = "# before\ndef f():\n    # inside\n    pass\n# after\n"
    blocks = find_comment_blocks_from_string(source)
    assert [block[0] for block in blocks] == [0, 2, 4]
    assert [block[4] for block in blocks] == ["# before", "# inside", "# after"]


@pytest.mark.parametrize("prefix", ['value = "é🐍"; ', "\t", 'value = "\x0b"; '])
def test_columns_are_characters_not_utf8_bytes(prefix):
    source = prefix + "# TODO: café\n"
    block = find_comment_blocks_from_string(source)[0]
    assert block[:4] == (0, len(prefix), 0, len(prefix) + len("# TODO: café"))
    assert extract_comment_text(source, block[:4]) == "# TODO: café"


def test_consecutive_inline_comments_do_not_capture_executable_code():
    source = "x = 1  # first\ny = 2  # second\n# continuation\n"
    blocks = find_comment_blocks_from_string(source)
    assert [block[4] for block in blocks] == ["# first", "# second\n# continuation"]
    assert all("y =" not in block[4] for block in blocks)


def test_multiline_slice_preserves_crlf_and_indentation():
    source = "if True:\r\n    # title\r\n    # body  \r\n    pass\r\n"
    block = find_comment_blocks_from_string(source)[0]
    assert block[4] == "# title\r\n    # body  "
    assert extract_comment_text(source, block[:4]) == block[4]


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_second_identical_tag_can_be_mutated_independently(tmp_path: Path, operation):
    source = "# TODO: repeated <priority=high>\nx = 1\n# TODO: repeated <priority=high>\n"
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    tags = string_to_data(source, file_path=path, schema=PureDataSchema)
    assert len(tags) == 2
    assert tags[0].offsets != tags[1].offsets
    if operation == "update":
        apply_mutations(path, [(tags[1], replace(tags[1], title="changed"))])
    else:
        delete_tags(path, [tags[1]])
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# TODO: repeated <priority=high>\nx = 1\n")
    assert text.count("repeated") == 1
    assert ("changed" in text) == (operation == "update")
