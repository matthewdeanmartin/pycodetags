import textwrap
from pathlib import Path

import pytest
from pycodetags_issue_tracker.schema.issue_tracker_schema import IssueTrackerSchema
from pycodetags_issue_tracker.schema.standard_code_tags import extract_comment_blocks_fallback as extract_comment_blocks

from pycodetags.common_interfaces import string_to_data_tag_typed_dicts
from pycodetags.data_tags.data_tags_methods import upgrade_to_specific_schema
from pycodetags.data_tags.data_tags_parsers import parse_codetags, parse_fields, promote_fields


# Helper function to create a dummy file for testing file operations
@pytest.fixture
def create_dummy_file(tmp_path):
    def _creator(filename, content):
        with open(tmp_path / filename, "w", encoding="utf-8") as f:
            f.write(content)
        return tmp_path / filename

    yield _creator
    # # Teardown: remove files created during tests
    # for f in os.listdir():
    #     if f.startswith("test_") and f.endswith(".py"):
    #         os.remove(f)


# Tests for parse_fields function
def test_parse_fields_basic():
    field_string = "priority:1 due:2025-12-31 assignee:john.doe"
    expected = {
        "default_fields": {},
        "data_fields": {
            "priority": "1",
            "due": "2025-12-31",
            "assignee": ["john.doe"],
        },
        "custom_fields": {},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


def test_parse_fields_with_aliases():
    field_string = "p:high d:2024-07-15 a:jane.doe,j.smith t:bugtracker"
    expected = {
        "default_fields": {},
        "data_fields": {
            "priority": "high",
            "due": "2024-07-15",
            "assignee": ["jane.doe", "j.smith"],
            "tracker": "bugtracker",
        },
        "custom_fields": {},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


def test_parse_fields_quoted_values():
    field_string = 'status:"In Progress" category:\'Feature Request\' custom: "some value with spaces"'
    expected = {
        "data_fields": {
            "status": "In Progress",
            "category": "Feature Request",
        },
        "default_fields": {},
        "custom_fields": {"custom": "some value with spaces"},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


def test_parse_fields_mixed_separators_and_spacing():
    # priorities are never CSV
    # assignee can be CSV
    field_string = "p = urgent assignee= bob.smith,  custom_field :  value "
    expected = {
        "data_fields": {
            "priority": "urgent",
            "assignee": ["bob.smith"],
        },
        "custom_fields": {"custom_field": "value"},
        "default_fields": {},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


def test_parse_fields_origination_date_and_assignee_initials():
    field_string = "2023-01-01 JRS assignee:user1"
    expected = {
        "data_fields": {
            "origination_date": "2023-01-01",
            "originator": "JRS",
            "assignee": ["user1"],
        },
        "default_fields": {
            "origination_date": "2023-01-01",
            "originator": "JRS",
        },
        "custom_fields": {},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    result = parse_fields(field_string, IssueTrackerSchema, strict=False)
    promote_fields({"fields": result}, IssueTrackerSchema)
    assert result == expected


def test_parse_fields_no_fields():
    field_string = ""
    expected = {
        "default_fields": {},
        "custom_fields": {},
        "data_fields": {},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


def test_parse_fields_only_custom_fields():
    field_string = "custom1:value1 custom2:value2"
    expected = {
        "default_fields": {},
        "data_fields": {},
        "custom_fields": {"custom1": "value1", "custom2": "value2"},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


def test_parse_fields_unquoted_value_stops_at_whitespace():
    # This test specifically addresses the change to `key_value_pattern`
    # to ensure unquoted values stop at whitespace.
    field_string = "p:1 2025-06-15"
    expected = {
        "data_fields": {
            "priority": "1",
            # parse_fields doesn't promote yet.
            # "origination_date": "2025-06-15",
        },
        "default_fields": {
            "origination_date": "2025-06-15",
        },
        "custom_fields": {},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


def test_parse_fields_multiple_assignees_comma_separated():
    field_string = "assignee:alice,bob,charlie"
    expected = {
        "data_fields": {"assignee": ["alice", "bob", "charlie"]},
        "custom_fields": {},
        "default_fields": {},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


@pytest.mark.skip("Merging default and alias not implemented yet")
def test_parse_fields_multiple_assignees_mixed():
    field_string = "assignee:alice A.B.C,D.E.F assignee:bob"
    expected = {
        "assignee": ["alice", "A.B.C", "D.E.F", "bob"],
        "custom_fields": {},
    }
    assert parse_fields(field_string, IssueTrackerSchema, False) == expected


# Tests for parse_codetags function
def test_parse_codetags_single_tag():
    text_block = "TODO: Implement this feature <priority:high due:2025-01-01>"
    results = parse_codetags(text_block, IssueTrackerSchema, strict=False)
    assert len(results) == 1
    assert results[0]["code_tag"] == "TODO"
    assert results[0]["comment"] == "Implement this feature"
    assert results[0]["fields"]["data_fields"]["priority"] == "high"
    assert results[0]["fields"]["data_fields"]["due"] == "2025-01-01"


def test_parse_codetags_multiple_tags_in_same_block():
    text_block = """
    # FIXME: This needs to be refactored <assignee:dev1 status:pending>
    # TODO: Add unit tests <priority:medium>
    # BUG: Critical issue <t:gh s:open>
    """
    results = parse_codetags(text_block, IssueTrackerSchema, strict=False)
    assert len(results) == 3

    assert results[0]["code_tag"] == "FIXME"
    assert results[0]["comment"] == "This needs to be refactored"
    assert results[0]["fields"]["data_fields"]["assignee"] == ["dev1"]
    assert results[0]["fields"]["data_fields"]["status"] == "pending"

    assert results[1]["code_tag"] == "TODO"
    assert results[1]["comment"] == "Add unit tests"
    assert results[1]["fields"]["data_fields"]["priority"] == "medium"

    assert results[2]["code_tag"] == "BUG"
    assert results[2]["comment"] == "Critical issue"
    assert results[2]["fields"]["data_fields"]["tracker"] == "gh"
    assert results[2]["fields"]["data_fields"]["status"] == "open"


def test_parse_codetags_with_multiline_comment_and_tag_on_single_line():
    text_block = """
    # This is a multiline comment.
    # It continues here.
    # TODO: Refactor this function to improve performance <priority:high>
    """
    results = parse_codetags(text_block, IssueTrackerSchema, strict=False)
    assert len(results) == 1
    assert results[0]["code_tag"] == "TODO"
    assert results[0]["comment"] == "Refactor this function to improve performance"
    assert results[0]["fields"]["data_fields"]["priority"] == "high"


def test_parse_codetags_no_tags():
    text_block = "This is just a regular comment."
    results = parse_codetags(text_block, IssueTrackerSchema, strict=False)
    assert len(results) == 0


def test_parse_codetags_malformed_tag():
    text_block = "TODO: Missing angle bracket"
    results = parse_codetags(text_block, IssueTrackerSchema, strict=False)
    assert len(results) == 0

    text_block = "TODO: comment <fields"
    results = parse_codetags(text_block, IssueTrackerSchema, strict=False)
    assert len(results) == 0


def test_parse_codetags_empty_field_string():
    text_block = "REVIEW: Check this code <>"
    results = parse_codetags(text_block, IssueTrackerSchema, strict=False)
    assert len(results) == 1
    assert results[0]["code_tag"] == "REVIEW"
    assert results[0]["comment"] == "Check this code"
    assert results[0]["fields"] == {
        "default_fields": {},
        "custom_fields": {},
        "data_fields": {},
        "identity_fields": [],
        "unprocessed_defaults": [],
    }


# Tests for extract_comment_blocks function
def test_extract_comment_blocks_basic(create_dummy_file):
    content = textwrap.dedent(
        """
        # Comment line 1
        # Comment line 2
        def func():
            # Another comment
            pass
        """
    )
    filename = create_dummy_file("test_comments.py", content)
    blocks = extract_comment_blocks(filename)
    assert len(blocks) == 2
    assert blocks[0] == ["# Comment line 1", "# Comment line 2"]
    assert blocks[1] == ["# Another comment"]


def test_extract_comment_blocks_no_comments(create_dummy_file):
    content = textwrap.dedent(
        """
        def func():
            pass
        class MyClass:
            def method(self):
                return 1
        """
    )
    filename = create_dummy_file("test_no_comments.py", content)
    blocks = extract_comment_blocks(filename)
    assert len(blocks) == 0


def test_extract_comment_blocks_only_comments(create_dummy_file):
    content = textwrap.dedent(
        """
        # Line 1
        # Line 2
        # Line 3
        """
    )
    filename = create_dummy_file("test_only_comments.py", content)
    blocks = extract_comment_blocks(filename)
    assert len(blocks) == 1
    assert blocks[0] == ["# Line 1", "# Line 2", "# Line 3"]


def test_extract_comment_blocks_separated_by_newline(create_dummy_file):
    content = textwrap.dedent(
        """
        # Comment block 1, line 1
        # Comment block 1, line 2

        # Comment block 2, line 1
        """
    )
    filename = create_dummy_file("test_separated_by_newline.py", content)
    blocks = extract_comment_blocks(filename)
    assert len(blocks) == 2
    assert blocks[0] == ["# Comment block 1, line 1", "# Comment block 1, line 2"]
    assert blocks[1] == ["# Comment block 2, line 1"]


def test_extract_comment_blocks_with_leading_and_trailing_whitespace(create_dummy_file):
    content = textwrap.dedent(
        """
        #   Comment with leading space
         # Comment with leading hash and space
        # Trailing space   
        """
    )
    filename = create_dummy_file("test_whitespace_comments.py", content)
    blocks = extract_comment_blocks(filename)
    assert len(blocks) == 1
    assert blocks[0] == [
        "#   Comment with leading space",
        "# Comment with leading hash and space",
        "# Trailing space",
    ]


# Tests for collect_pep350_code_tags function
def test_collect_pep350_code_tags_single_file(create_dummy_file):
    content = textwrap.dedent(
        """
        # TODO: Finish this module <priority:high assignee:dev_a>
        # A regular comment
        # FIXME: Refactor this part <due:2025-06-30>
        def some_function():
            # BUG: This might cause an error in production <status:open c:critical>
            pass
        """
    )
    filename = create_dummy_file("test_single_file.py", content)
    tags = list(
        upgrade_to_specific_schema(_, IssueTrackerSchema, flat=False)
        for _ in string_to_data_tag_typed_dicts(content, Path(filename), schema=IssueTrackerSchema)
    )

    assert len(tags) == 3

    assert tags[0]["code_tag"] == "TODO"
    assert tags[0]["comment"] == "Finish this module"
    assert tags[0]["fields"]["data_fields"]["priority"] == "high"
    assert tags[0]["fields"]["data_fields"]["assignee"] == ["dev_a"]

    assert tags[1]["code_tag"] == "FIXME"
    assert tags[1]["comment"] == "Refactor this part"
    assert tags[1]["fields"]["data_fields"]["due"] == "2025-06-30"

    assert tags[2]["code_tag"] == "BUG"
    assert tags[2]["comment"] == "This might cause an error in production"
    assert tags[2]["fields"]["data_fields"]["status"] == "open"
    assert tags[2]["fields"]["data_fields"]["category"] == "critical"


def test_collect_pep350_code_tags_multiple_tags_same_line(create_dummy_file):
    content = textwrap.dedent(
        """
        # TODO: Task 1 <p:1> FIXME: Task 2 <p:2>
        # BUG: Issue <s:new>
        """
    )
    filename = create_dummy_file("test_multiple_tags_same_line.py", content)
    tags = list(
        upgrade_to_specific_schema(_, IssueTrackerSchema, flat=False)
        for _ in string_to_data_tag_typed_dicts(content, Path(filename), schema=IssueTrackerSchema)
    )

    assert len(tags) == 3  # Two from the first line, one from the second

    assert tags[0]["code_tag"] == "TODO"
    assert tags[0]["comment"] == "Task 1"
    assert tags[0]["fields"]["data_fields"]["priority"] == "1"

    assert tags[1]["code_tag"] == "FIXME"
    assert tags[1]["comment"] == "Task 2"
    assert tags[1]["fields"]["data_fields"]["priority"] == "2"

    assert tags[2]["code_tag"] == "BUG"
    assert tags[2]["comment"] == "Issue"
    assert tags[2]["fields"]["data_fields"]["status"] == "new"


def test_collect_pep350_code_tags_no_tags_in_file(create_dummy_file):
    content = textwrap.dedent(
        """
        # This is a normal comment.
        # Another normal comment.
        def nothing_special():
            pass
        """
    )
    filename = create_dummy_file("test_no_tags.py", content)
    tags = list(
        upgrade_to_specific_schema(_, IssueTrackerSchema, flat=False)
        for _ in string_to_data_tag_typed_dicts(content, Path(filename), schema=IssueTrackerSchema)
    )
    assert len(tags) == 0


def test_collect_pep350_code_tags_empty_file(create_dummy_file):
    filename = create_dummy_file("test_empty.py", "")
    tags = list(
        upgrade_to_specific_schema(_, IssueTrackerSchema, flat=False)
        for _ in string_to_data_tag_typed_dicts("", Path(filename), schema=IssueTrackerSchema)
    )
    assert len(tags) == 0


def test_collect_pep350_code_tags_with_mixed_content(create_dummy_file):
    content = textwrap.dedent(
        """
# Initial comment
# TODO: First task <p:high>
import os
# Some code here
def my_func():
    # BUG: Problem in func <s:open a:dev_b>
    print("hello")
# Another block
# FIXME: Final fix <d:2026-01-01>
"""
    )
    filename = create_dummy_file("test_mixed_content.py", content)
    tags = list(
        upgrade_to_specific_schema(_, IssueTrackerSchema, flat=False)
        for _ in string_to_data_tag_typed_dicts(content, Path(filename), schema=IssueTrackerSchema)
    )

    assert len(tags) == 3

    todo_tag = list(filter(lambda x: x["code_tag"] == "TODO", tags))[0]
    assert todo_tag["code_tag"] == "TODO"
    assert todo_tag["comment"] == "First task"
    assert todo_tag["fields"]["data_fields"]["priority"] == "high"

    bug_tag = list(filter(lambda x: x["code_tag"] == "BUG", tags))[0]
    assert bug_tag["code_tag"] == "BUG"
    assert bug_tag["comment"] == "Problem in func"
    assert bug_tag["fields"]["data_fields"]["status"] == "open"
    assert bug_tag["fields"]["data_fields"]["assignee"] == ["dev_b"]

    fixme_tag = list(filter(lambda x: x["code_tag"] == "FIXME", tags))[0]
    assert fixme_tag["code_tag"] == "FIXME"
    assert fixme_tag["comment"] == "Final fix"
    assert fixme_tag["fields"]["data_fields"]["due"] == "2026-01-01"


def test_parse_fields_originator_field():
    field_string = "originator:john.doe"
    expected = {
        "default_fields": {},
        "custom_fields": {},
        "data_fields": {
            "originator": "john.doe",
        },
        "identity_fields": [],
        "unprocessed_defaults": [],
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


@pytest.mark.skip("Quotes behavior is undefined in spec.")
def test_parse_fields_quotes_with_escaped_chars():
    field_string = r"""custom:"value with \"quotes\" and \'single quotes\'" """
    expected = {
        "default_fields": {},
        "custom_fields": {"custom": r'value with "quotes" and \'single quotes\''},
    }
    assert parse_fields(field_string, IssueTrackerSchema, strict=False) == expected


# def test_parse_fields_single_quote_with_escaped_chars():
#     field_string = r"custom:'value with \'quotes\' and \"double quotes\"' "
#     expected = {
#         "default_fields": {},
#         "custom_fields": {"custom": r"value with 'quotes' and \"double quotes\""},
#     }
#     assert parse_fields(field_string) == expected
