import pytest

from pycodetags.data_tags import (
    get_data_field_value,
    is_int,
    merge_two_dicts,
    parse_codetags,
    parse_fields,
    promote_fields,
)


@pytest.mark.parametrize(
    "s,expected",
    [
        ("123", True),
        ("-456", True),
        ("+789", True),
        ("12.3", False),
        ("abc", False),
        ("", False),
    ],
)
def test_is_int_behavior(s, expected):
    assert is_int(s) == expected


def schema_stub():
    return {
        "default_fields": {"date": "origination_date", "str": "assignee"},
        "data_fields": {"priority": "str", "category": "str", "assignee": "str"},
        "data_field_aliases": {"p": "priority", "c": "category", "a": "assignee"},
    }


def test_parse_fields_typical_case():
    field_string = 'p:high c:"long term" origin:today JD 2025-06-15'
    fields = parse_fields(field_string, schema_stub(), strict=False)
    assert fields["data_fields"]["priority"] == "high"
    assert fields["data_fields"]["category"] == "long term"
    assert fields["custom_fields"]["origin"] == "today"
    assert "JD" in fields["default_fields"]["assignee"]
    assert fields["default_fields"]["origination_date"] == "2025-06-15"


def test_parse_fields_handles_quoted_values():
    field_string = 'c:"foo bar" x:"1:2:3" y:"she said \'hi\' today"'
    fields = parse_fields(field_string, schema_stub(), strict=False)
    assert fields["data_fields"]["category"] == "foo bar"
    assert fields["custom_fields"]["x"] == "1:2:3"
    assert "she said 'hi' today" in fields["custom_fields"]["y"]


def test_get_data_field_value_single_value():
    fields = {
        "data_fields": {"priority": "high"},
        "custom_fields": {},
        "default_fields": {},
        "strict": False,
    }
    assert get_data_field_value(schema_stub(), fields, "priority") == "high"


def test_get_data_field_value_conflict_strict_raises():
    fields = {
        "data_fields": {"priority": "high"},
        "custom_fields": {"priority": "low"},
        "default_fields": {},
        "strict": True,
    }
    with pytest.raises(TypeError):
        get_data_field_value(schema_stub(), fields, "priority")


# Test pollution, this changes global state and causes other tests to faial
# def test_get_data_field_value_conflict_warns(caplog):
#     # this persists after test!
#     caplog.set_level(logging.INFO)
#
#     fields = {
#         "data_fields": {"priority": "high"},
#         "custom_fields": {"priority": "low"},
#         "default_fields": {},
#         "strict": False,
#     }
#     with caplog.at_level(logging.WARNING):
#         val = get_data_field_value(schema_stub(), fields, "priority")
#         assert val == "high"
#         assert "Double field with different values" in caplog.text


def test_promote_fields_merges_and_removes_custom():
    tag = {
        "code_tag": "TAG",
        "comment": "test",
        "fields": {
            "default_fields": {"assignee": ["JD"], "origination_date": "2025-06-15"},
            "data_fields": {"priority": "high"},
            "custom_fields": {"p": "low"},
            "strict": False,
        },
    }
    promote_fields(tag, schema_stub())
    assert "priority" in tag["fields"]["data_fields"]
    assert tag["fields"]["data_fields"]["priority"] == ["high", "low"]
    assert "p" not in tag["fields"]["custom_fields"]


def test_merge_two_dicts_simple():
    d1 = {"a": 1}
    d2 = {"b": 2}
    result = merge_two_dicts(d1, d2)
    assert result == {"a": 1, "b": 2}


def test_parse_codetags_single_line():
    text = "# TODO: refactor this <p:high a:JD 2025-06-15>"
    result = parse_codetags(text, schema_stub(), strict=False)
    assert len(result) == 1
    tag = result[0]
    assert tag["code_tag"] == "TODO"
    assert tag["comment"] == "refactor this"
    assert tag["fields"]["data_fields"]["priority"] == "high"
    assert tag["fields"]["default_fields"]["origination_date"] == "2025-06-15"


def test_parse_codetags_multiline_and_wrapped():
    text = """# BUG: major flaw
    # <p:high
    #    a:JD
    #    2025-06-15>
    """
    result = parse_codetags(text, schema_stub(), strict=False)
    assert len(result) == 1
    tag = result[0]
    assert tag["code_tag"] == "BUG"
    assert tag["fields"]["data_fields"]["priority"] == "high"
    assert "JD" in tag["fields"]["data_fields"]["assignee"]
