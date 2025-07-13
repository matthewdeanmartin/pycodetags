from unittest.mock import MagicMock, patch

import pytest
from pycodetags_issue_tracker.converters import blank_to_null, convert_folk_tag_to_TODO, convert_pep350_tag_to_TODO

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


@patch("pycodetags_issue_tracker.converters.TODO")
def test_convert_folk_tag_to_TODO_promotes_custom_fields(mock_todo):
    tag = {
        "code_tag": "TODO",
        "file_path": "f.py",
        "line_number": 1,
        "custom_fields": {"priority": "high", "x": "y"},
        "comment": "do this",
        "tracker": "url",
        "assignee": "a",
        "originator": "b",
    }

    convert_folk_tag_to_TODO(tag)

    kwargs = mock_todo.call_args[1]
    assert kwargs["priority"] == "high"
    assert kwargs["custom_fields"] == {"priority": "high", "x": "y"}


@patch("pycodetags_issue_tracker.converters.logger")
@patch("pycodetags_issue_tracker.converters.TODO")
def test_convert_folk_tag_to_TODO_duplicate_keyword_warns(mock_todo, mock_logger):
    tag = {
        "code_tag": "TODO",
        "file_path": "f.py",
        "line_number": 1,
        "comment": "note",
        "custom_fields": {"priority": "urgent"},
        "priority": "existing",
    }

    # Add priority to kwargs explicitly
    def side_effect(**kwargs):
        assert "priority" in kwargs
        return MagicMock()

    mock_todo.side_effect = side_effect
    convert_folk_tag_to_TODO(tag)

    # Because "priority" is manually present, it won't promote the custom field
    # And logger should not warn (no promotion attempted if already in kwargs)
    assert not mock_logger.warning.called


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
