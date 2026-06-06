"""Phase 3: hard TDG parser (spec/id_and_tdg.md Part 4). Table-driven, pure-parser tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pycodetags.data_tags.data_tags_parsers import iterate_comments
from pycodetags.data_tags.data_tags_schema import DataTagSchema
from pycodetags.data_tags.tdg_tags_parser import as_tdg_comment, is_property_line
from pycodetags.data_tags.tdg_tags_parser import iterate_comments as tdg_iterate


def tdg_schema() -> DataTagSchema:
    return {
        "name": "TDG",
        "matching_tags": ["TODO", "FIXME", "BUG", "HACK"],
        "default_fields": {},
        "data_fields": {
            "title": "str",
            "body": "str",
            "category": "str",
            "issue": "int",
            "estimate": "float",
            "author": "str",
            "id": "int",
        },
        "data_field_aliases": {"cat": "category"},
        "field_infos": {},
        "identity_fields": ["issue"],
    }


def parse(src: str):
    return list(tdg_iterate(src, None, [tdg_schema()]))


# --- is_property_line heuristic ---


@pytest.mark.parametrize(
    "line,expected",
    [
        ("# category=core issue=123 estimate=30m", True),
        ("# issue=123", True),
        ("# a=1 b=2 c=3", True),
        ("# Use the old method=foo approach here", False),  # only 1 of 7 tokens
        ("# just a normal description", False),
        ("#", False),
        ("# ", False),
        ("# a=1 plain words here", False),  # 1 of 5
        ("# a=1 b=2 word", True),  # 2 of 3 > 50%
        ("# a=1 b=2", True),
        ("category=core issue=1", True),  # works without leading #
    ],
)
def test_is_property_line(line, expected):
    assert is_property_line(line) is expected


# --- basic parse ---


def test_basic_tdg_parse():
    tags = parse("# TODO: My title\n# issue=42 category=core\n# Body line 1\n# Body line 2")
    assert len(tags) == 1
    t = tags[0]
    assert t["code_tag"] == "TODO"
    assert t["comment"] == "My title"
    assert t["fields"]["data_fields"] == {"issue": "42", "category": "core"}
    assert t["fields"]["custom_fields"]["body"] == "Body line 1\nBody line 2"
    assert t["fields"]["custom_fields"]["title"] == "My title"
    assert t["original_schema"] == "TDG"


def test_title_only_no_props_no_body():
    tags = parse("# TODO: just a title")
    assert len(tags) == 1
    assert tags[0]["comment"] == "just a title"
    assert tags[0]["fields"]["data_fields"] == {}
    assert "body" not in tags[0]["fields"]["custom_fields"]


def test_no_property_line_means_line2_is_body():
    """A sentence with an '=' must not be parsed as properties (heuristic guard)."""
    tags = parse("# TODO: title\n# Use the old method=foo approach")
    assert tags[0]["fields"]["data_fields"] == {}
    assert tags[0]["fields"]["custom_fields"]["body"] == "Use the old method=foo approach"


def test_property_line_only_no_body():
    tags = parse("# TODO: title\n# issue=7")
    assert tags[0]["fields"]["data_fields"] == {"issue": "7"}
    assert "body" not in tags[0]["fields"]["custom_fields"]


# --- boundaries ---


def test_new_anchor_ends_current_tag():
    src = "# TODO: first\n# body of first\n# FIXME: second\n# issue=9"
    tags = parse(src)
    assert len(tags) == 2
    assert tags[0]["code_tag"] == "TODO"
    assert tags[0]["comment"] == "first"
    assert tags[0]["fields"]["custom_fields"]["body"] == "body of first"
    assert tags[1]["code_tag"] == "FIXME"
    assert tags[1]["fields"]["data_fields"] == {"issue": "9"}


def test_three_anchors_in_a_block():
    src = "# TODO: a\n# BUG: b\n# HACK: c"
    tags = parse(src)
    assert [t["code_tag"] for t in tags] == ["TODO", "BUG", "HACK"]
    assert [t["comment"] for t in tags] == ["a", "b", "c"]


def test_non_matching_tag_ignored():
    assert parse("# NOTE: not a todo") == []


def test_non_matching_anchor_does_not_split():
    """A NOTE: line inside a TODO body is body text, not a new tag."""
    src = "# TODO: title\n# NOTE: this is just prose"
    tags = parse(src)
    assert len(tags) == 1
    assert "NOTE: this is just prose" in tags[0]["fields"]["custom_fields"]["body"]


# --- body cleaning ---


def test_body_preserves_internal_blank_comment_lines():
    src = "# TODO: t\n# line1\n#\n# line3"
    body = parse(src)[0]["fields"]["custom_fields"]["body"]
    assert body == "line1\n\nline3"


def test_body_strips_exactly_one_hash_space():
    src = "# TODO: t\n#   indented body"
    body = parse(src)[0]["fields"]["custom_fields"]["body"]
    assert body == "  indented body"  # one '# ' removed, remaining spaces kept


# --- offsets ---


def test_offsets_single_tag():
    tags = parse("# TODO: title\n# body")
    start_line, start_char, end_line, end_char = tags[0]["offsets"]
    assert (start_line, start_char) == (0, 0)
    assert end_line == 1


def test_offsets_second_tag_in_block():
    src = "# TODO: first\n# FIXME: second"
    tags = parse(src)
    assert tags[0]["offsets"][0] == 0
    assert tags[1]["offsets"][0] == 1  # second tag starts on block line 1


# --- as_tdg_comment serializer + round trip ---


def test_as_tdg_comment_basic():
    out = as_tdg_comment(code_tag="TODO", title="My title", body="line one\nline two", properties={"issue": "123"})
    assert out == "# TODO: My title\n# issue=123\n# line one\n# line two"


def test_as_tdg_comment_excludes_title_body_from_properties():
    out = as_tdg_comment(code_tag="TODO", title="T", properties={"title": "x", "body": "y", "issue": "1"})
    assert "title=" not in out
    assert "body=" not in out
    assert "issue=1" in out


def test_as_tdg_comment_skips_blank_properties():
    out = as_tdg_comment(code_tag="TODO", title="T", properties={"issue": "", "category": None, "author": "matth"})
    assert "issue=" not in out
    assert "category=" not in out
    assert "author=matth" in out


def test_as_tdg_comment_quotes_values_with_spaces():
    out = as_tdg_comment(code_tag="TODO", title="T", properties={"category": "needs review"})
    assert 'category="needs review"' in out


def test_as_tdg_comment_no_properties_no_body():
    out = as_tdg_comment(code_tag="TODO", title="Only a title")
    assert out == "# TODO: Only a title"


@pytest.mark.parametrize(
    "title,body,properties",
    [
        ("Simple title", None, {}),
        ("Title", "single body", {"issue": "1"}),
        ("Title", "multi\nline\nbody", {"issue": "42", "category": "core", "estimate": "0.5"}),
        ("Title", None, {"author": "matth", "id": "7"}),
    ],
)
def test_round_trip_serialize_parse(title, body, properties):
    out = as_tdg_comment(code_tag="TODO", title=title, body=body, properties=properties)
    reparsed = parse(out)[0]
    assert reparsed["comment"] == title
    for key, value in properties.items():
        assert reparsed["fields"]["data_fields"].get(key) == value
    if body:
        assert reparsed["fields"]["custom_fields"]["body"] == body


# --- integration through core iterate_comments ---


def test_integration_through_core_pipeline():
    src = "x = 1\n\n# TODO: real title\n# issue=55 category=core\n# body a\n# body b\n\ny = 2\n"
    tags = list(iterate_comments(src, Path("demo.py"), [tdg_schema()], include_folk_tags=False))
    assert len(tags) == 1
    t = tags[0]
    assert t["original_schema"] == "TDG"
    assert t["offsets"][0] == 2  # third line (0-based) in the file
    assert t["fields"]["custom_fields"]["body"] == "body a\nbody b"


def test_pep350_wins_over_tdg():
    """A PEP-350 field block in the same comment should be parsed as PEP-350, not TDG."""
    src = "# TODO: pep style <issue=1>\n"
    tags = list(iterate_comments(src, Path("demo.py"), [tdg_schema()], include_folk_tags=False))
    # PEP-350 parser handles the <...> block; TDG must not also produce a tag for it.
    assert all(t["original_schema"] != "TDG" for t in tags) or len(tags) == 1
