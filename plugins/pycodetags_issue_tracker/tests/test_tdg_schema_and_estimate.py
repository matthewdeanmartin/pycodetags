"""Phase 2: TDG schema registration + converter lifting (spec/id_and_tdg.md Part 3)."""

from __future__ import annotations

import pytest
from pycodetags_issue_tracker.converters import convert_data_to_TODO, parse_estimate
from pycodetags_issue_tracker.main import IssueTrackerApp
from pycodetags_issue_tracker.schema.tdg_schema import TDGSchema

from pycodetags.data_tags.data_tags_classes import DATA


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("30m", 0.5),
        ("2h", 2.0),
        ("90m", 1.5),
        ("1.5", 1.5),
        ("1.5h", 1.5),
        (None, None),
        ("", None),
        ("   ", None),
        ("soon", None),
        (3, 3.0),
    ],
)
def test_parse_estimate(raw, expected):
    assert parse_estimate(raw) == expected


def test_provide_schemas_includes_tdg():
    schemas = IssueTrackerApp().provide_schemas()
    names = {s["name"] for s in schemas}
    assert "TODO" in names
    assert "TDG" in names


def test_tdg_schema_identity_is_issue():
    assert TDGSchema["identity_fields"] == ["issue"]
    assert "issue" in TDGSchema["data_fields"]
    assert "title" in TDGSchema["data_fields"]
    assert "body" in TDGSchema["data_fields"]


def test_converter_lifts_title_body_from_attributes():
    tag = DATA(code_tag="TODO", comment="t", title="The Title", body="The Body")
    todo = convert_data_to_TODO(tag)
    assert todo.title == "The Title"
    assert todo.body == "The Body"


def test_converter_lifts_tdg_fields_from_custom_fields():
    tag = DATA(
        code_tag="TODO",
        comment="t",
        custom_fields={"issue": "42", "estimate": "45m", "id": "7", "title": "T", "body": "B"},
    )
    todo = convert_data_to_TODO(tag)
    assert todo.issue == "42"
    assert todo.estimate == 0.75
    assert todo.tag_id == "7"
    assert todo.title == "T"
    assert todo.body == "B"


def test_converter_attribute_wins_over_custom_field_for_title():
    tag = DATA(code_tag="TODO", comment="t", title="attr", custom_fields={"title": "custom"})
    todo = convert_data_to_TODO(tag)
    assert todo.title == "attr"


def test_get_from_custom_or_data_checks_custom_fields():
    """Regression: get_from_custom_or_data previously checked data_fields twice, never custom."""
    from pycodetags_issue_tracker.converters import get_from_custom_or_data

    tag = DATA(code_tag="TODO", comment="t", custom_fields={"only_in_custom": "yes"})
    assert get_from_custom_or_data("only_in_custom", tag) == "yes"
