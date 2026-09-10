"""TDG offsets must identify the exact source slice passed to the mutation API."""

from dataclasses import replace

import pytest

from pycodetags.common_interfaces import string_to_data
from pycodetags.data_tags.tdg_tags_parser import iterate_comments
from pycodetags.id_command import tdg_serializer
from pycodetags.mutator import apply_mutations
from pycodetags.python.comment_finder import extract_comment_text

TDG_SCHEMA = {
    "name": "TDG",
    "format": "TDG",
    "matching_tags": ["TODO"],
    "default_fields": {},
    "data_fields": {"issue": "int", "id": "int", "tracker": "str"},
    "data_field_aliases": {},
    "field_infos": {},
    "identity_fields": [],
}


@pytest.mark.parametrize("prefix", ["    ", "\t", 'value = "🐍"; '])
def test_single_line_tdg_end_column_includes_source_prefix(prefix):
    source = prefix + "# TODO: title\n"
    tags = string_to_data(source, schema=TDG_SCHEMA)
    assert len(tags) == 1
    tag = tags[0]
    assert tag.offsets == (0, len(prefix), 0, len(prefix) + len("# TODO: title"))
    assert extract_comment_text(source, tag.offsets) == tag.original_text == "# TODO: title"


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_direct_parser_preserves_exact_indented_slice(newline):
    source = newline.join(["    # TODO: title", "    # issue=100", "    # body  "])
    tag = list(iterate_comments(source, None, [TDG_SCHEMA]))[0]
    assert extract_comment_text(source, tag["offsets"]) == tag["original_text"]
    assert tag["original_text"].startswith("# TODO")
    assert tag["original_text"].endswith("body  ")


def test_indented_single_line_tdg_can_be_updated(tmp_path):
    source = "def f():\n    # TODO: title\n    pass\n"
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    tag = string_to_data(source, file_path=path, schema=TDG_SCHEMA)[0]
    apply_mutations(path, [(tag, replace(tag, title="updated"))], serializer=tdg_serializer)
    assert path.read_text(encoding="utf-8") == "def f():\n    # TODO: updated\n    pass\n"
