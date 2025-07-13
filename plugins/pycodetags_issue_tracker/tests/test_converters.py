from unittest.mock import patch

import pytest
from pycodetags_issue_tracker.converters import blank_to_null, convert_pep350_tag_to_TODO

from pycodetags import DataTag

# -- blank_to_null tests --


@pytest.mark.parametrize(
    "val,expected",
    [
        ("", None),
        ("   ", None),
        (None, None),
        ("x", "x"),
        (" x ", "x"),
    ],
)
def test_blank_to_null(val, expected):
    assert blank_to_null(val) == expected


# -- convert_folk_tag_to_TODO tests --


# -- convert_pep350_tag_to_TODO tests --


@patch("pycodetags_issue_tracker.converters.TODO")
def test_convert_pep350_tag_to_TODO_field_promotion(mock_todo):
    tag: DataTag = {
        "code_tag": "NOTE",
        "comment": "x",
        "fields": {
            "default_fields": {},
            "custom_fields": {"blah": "in-progress"},
            "data_fields": {
                "assignee": "a",
                "originator": "b",
                "due": "soon",
            },
        },
    }

    convert_pep350_tag_to_TODO(tag)

    kwargs = mock_todo.call_args[1]
    assert kwargs["custom_fields"]["blah"] == "in-progress"
    assert kwargs["custom_fields"] == {"blah": "in-progress"}


@patch("pycodetags_issue_tracker.converters.logger")
@patch("pycodetags_issue_tracker.converters.TODO")
def test_convert_pep350_tag_to_TODO_duplicate_warns(mock_todo, mock_logger):
    tag = {
        "code_tag": "XXX",
        "comment": "a",
        "fields": {
            "default_fields": {},
            "data_fields": {"priority": "explicit"},
            "custom_fields": {"priority": "from_field"},
        },
    }

    convert_pep350_tag_to_TODO(tag)

    # Should not log warning since explicit key blocks promotion
    assert not mock_logger.warning.called
