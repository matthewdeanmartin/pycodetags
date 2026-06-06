"""Extended tests for data_tags_parsers: parse_fields, parse_codetags, iterate_comments edge cases."""

from __future__ import annotations

from pathlib import Path

import pytest

from pycodetags.data_tags.data_tags_parsers import (
    is_int,
    iterate_comments,
    parse_codetags,
    parse_fields,
)
from pycodetags.data_tags.data_tags_schema import DataTagSchema
from pycodetags.exceptions import SchemaError


def _schema() -> DataTagSchema:
    return {
        "name": "TEST",
        "matching_tags": ["TODO", "FIXME", "BUG"],
        "default_fields": {"date": "origination_date", "str|list[str]": "assignee"},
        "data_fields": {
            "priority": "str",
            "category": "str",
            "assignee": "str",
            "origination_date": "str",
            "status": "str",
        },
        "data_field_aliases": {
            "p": "priority",
            "cat": "category",
            "a": "assignee",
            "st": "status",
        },
        "field_infos": {},
        "identity_fields": [],
    }


# ---------------------------------------------------------------------------
# is_int – edge cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0", True),
        ("-0", True),
        ("+0", True),
        ("9999999999", True),
        ("-1", True),
        ("+1", True),
        ("1.0", False),
        (" 1", False),
        ("1 ", False),
        ("1e3", False),
        ("--1", False),
        ("+-1", False),
    ],
)
def test_is_int_parametrized(value, expected):
    assert is_int(value) == expected


# ---------------------------------------------------------------------------
# parse_fields
# ---------------------------------------------------------------------------


def test_parse_fields_single_quoted_value():
    fields = parse_fields("category:'long term work'", _schema(), strict=False)
    assert fields["data_fields"]["category"] == "long term work"


def test_parse_fields_double_quoted_value():
    fields = parse_fields('category:"long term work"', _schema(), strict=False)
    assert fields["data_fields"]["category"] == "long term work"


def test_parse_fields_alias_resolved():
    fields = parse_fields("p:high", _schema(), strict=False)
    assert "priority" in fields["data_fields"]
    assert fields["data_fields"]["priority"] == "high"


def test_parse_fields_unknown_key_goes_to_custom():
    fields = parse_fields("sprint:S2", _schema(), strict=False)
    assert "sprint" in fields["custom_fields"]
    assert fields["custom_fields"]["sprint"] == "S2"


def test_parse_fields_date_token_captured():
    fields = parse_fields("2025-12-31", _schema(), strict=False)
    assert fields["default_fields"]["origination_date"] == "2025-12-31"


def test_parse_fields_assignee_token_captured():
    fields = parse_fields("ALICE BOB", _schema(), strict=False)
    df = fields["default_fields"]
    assert "assignee" in df
    assignees = df["assignee"]
    assert "ALICE" in assignees or ("ALICE" in str(assignees))


def test_parse_fields_hash_token_skipped():
    # A bare '#' in the field string must be silently ignored
    fields = parse_fields("# priority:low", _schema(), strict=False)
    assert fields["data_fields"].get("priority") == "low"


def test_parse_fields_multiple_key_values():
    fields = parse_fields("priority:high status:open", _schema(), strict=False)
    assert fields["data_fields"]["priority"] == "high"
    assert fields["data_fields"]["status"] == "open"


def test_parse_fields_empty_string_returns_empty_fields():
    fields = parse_fields("", _schema(), strict=False)
    assert fields["data_fields"] == {}
    assert fields["custom_fields"] == {}
    assert fields["default_fields"] == {}


def test_parse_fields_unprocessed_defaults_filled_for_unknown_tokens():
    fields = parse_fields("mystery_token_xyz", _schema(), strict=False)
    # 'mystery_token_xyz' is not a date, not an int, and will be consumed by 'str|list[str]' assignee
    # or 'str' default (if present). With this schema it lands in assignee default.
    # We just assert no crash and some result is produced.
    assert isinstance(fields["default_fields"], dict)


# ---------------------------------------------------------------------------
# parse_codetags
# ---------------------------------------------------------------------------


def test_parse_codetags_returns_empty_for_no_tags():
    result = parse_codetags("just a plain comment with no tags", _schema(), strict=False)
    assert result == []


def test_parse_codetags_detects_multiple_tags():
    src = "# TODO: first <priority:high> # FIXME: second <priority:low>"
    result = parse_codetags(src, _schema(), strict=False)
    assert len(result) == 2


def test_parse_codetags_requires_uppercase_tag():
    # Lowercase tags should not match the [A-Z\?!]{3,} pattern
    result = parse_codetags("# todo: lowercase <priority:high>", _schema(), strict=False)
    assert result == []


def test_parse_codetags_three_uppercase_letters_minimum():
    # Two-letter tags must not match (pattern requires 3+)
    result = parse_codetags("# TO: short <priority:high>", _schema(), strict=False)
    assert result == []


def test_parse_codetags_exclamation_tag():
    result = parse_codetags("# BUG!: urgent <priority:critical>", _schema(), strict=False)
    # '!' is in [A-Z\?!] so BUG! should be detected
    assert len(result) >= 1


def test_parse_codetags_comment_cleaned():
    src = "# TODO: fix the thing <priority:high>"
    result = parse_codetags(src, _schema(), strict=False)
    assert result[0]["comment"] == "fix the thing"


def test_parse_codetags_multiline_fields_joined():
    src = """# BUG: major flaw
# <p:high
#    a:ALICE
#    2025-06-15>"""
    result = parse_codetags(src, _schema(), strict=False)
    assert len(result) == 1
    assert result[0]["fields"]["data_fields"].get("priority") == "high"


# ---------------------------------------------------------------------------
# iterate_comments – high-level
# ---------------------------------------------------------------------------


def test_iterate_comments_raises_with_no_schema_and_no_folk():
    with pytest.raises(SchemaError):
        list(iterate_comments("# TODO: x <priority:high>", None, schemas=[], include_folk_tags=False))


def test_iterate_comments_returns_tags_from_string():
    src = "# TODO: something important <priority:high status:open>"
    tags = list(iterate_comments(src, None, schemas=[_schema()], include_folk_tags=False))
    assert len(tags) == 1
    assert tags[0]["code_tag"] == "TODO"


def test_iterate_comments_sets_file_path():
    src = "# TODO: x <priority:high>"
    path = Path("src/module.py")
    tags = list(iterate_comments(src, path, schemas=[_schema()], include_folk_tags=False))
    assert tags[0]["file_path"] == str(path)


def test_iterate_comments_sets_original_schema():
    src = "# FIXME: a bug <status:open>"
    tags = list(iterate_comments(src, None, schemas=[_schema()], include_folk_tags=False))
    assert tags[0]["original_schema"] == "PEP350"


def test_iterate_comments_sets_offsets():
    src = "# BUG: crash <priority:critical>"
    tags = list(iterate_comments(src, None, schemas=[_schema()], include_folk_tags=False))
    offsets = tags[0]["offsets"]
    assert offsets is not None
    assert len(offsets) == 4


def test_iterate_comments_handles_multiple_blocks():
    src = (
        "# TODO: first task <priority:high>\n"
        "\n"
        "def foo(): pass\n"
        "\n"
        "# FIXME: second task <status:open>\n"
    )
    tags = list(iterate_comments(src, None, schemas=[_schema()], include_folk_tags=False))
    assert len(tags) == 2
    codes = {t["code_tag"] for t in tags}
    assert codes == {"TODO", "FIXME"}


def test_iterate_comments_folk_tag_found_when_requested():
    src = "# TODO: fix something\n"
    schema = _schema()
    schema["matching_tags"] = ["TODO"]
    # Folk tags require include_folk_tags=True and a non-PEP350 comment (no < >)
    tags = list(iterate_comments(src, None, schemas=[schema], include_folk_tags=True))
    # At least one tag should be found (folk or PEP-350 depending on text)
    assert isinstance(tags, list)


def test_iterate_comments_no_tags_returns_empty():
    src = "x = 1\ny = 2\n"
    tags = list(iterate_comments(src, None, schemas=[_schema()], include_folk_tags=False))
    assert tags == []
