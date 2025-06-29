from pycodetags_issue_tracker.converters import convert_pep350_tag_to_TODO
from pycodetags_issue_tracker.specific_schemas import PEP350Schema

from pycodetags.data_tags import parse_codetags


def test_single_line_fixme_tag():
    input_text = "# FIXME: Seems like this Loop should be finite. <MDE, CLE d:2015-1-1 p:2>"
    result = parse_codetags(input_text, PEP350Schema, strict=False)
    assert result == [
        {
            "code_tag": "FIXME",
            "comment": "Seems like this Loop should be finite.",
            "fields": {
                "default_fields": {"assignee": ["MDE", "CLE"]},
                "data_fields": {
                    "assignee": ["MDE", "CLE"],
                    "priority": "2",
                    "due": "2015-1-1",
                },
                "custom_fields": {},
                "strict": False,
            },
            "original_text": "N/A",
        }
    ]
    for tag in result:
        convert_pep350_tag_to_TODO(tag)


def test_inline_bug_tag():
    input_text = "while True: # BUG: Crashes if run on Sundays. <MDE 2005-09-04 d:2015-6-6 p:2>"
    result = parse_codetags(input_text, PEP350Schema, strict=False)
    assert result == [
        {
            "code_tag": "BUG",
            "comment": "Crashes if run on Sundays.",
            "fields": {
                "default_fields": {
                    "assignee": ["MDE"],
                    "origination_date": "2005-09-04",
                },
                "data_fields": {
                    "assignee": ["MDE"],
                    "due": "2015-6-6",
                    "priority": "2",
                    "origination_date": "2005-09-04",
                },
                "custom_fields": {},
                "strict": False,
            },
            "original_text": "N/A",
        }
    ]
    for tag in result:
        convert_pep350_tag_to_TODO(tag)


def test_multiline_todo_tag():
    input_text = """
    # TODO: This is a complex task that needs more details.
    # <
    #   assignee=JRNewbie
    #   priority:3
    #   due=2025-12-25
    #   custom_field: some_value
    # >
    """
    result = parse_codetags(input_text, PEP350Schema, strict=False)
    assert result == [
        {
            "code_tag": "TODO",
            "comment": "This is a complex task that needs more details.",
            "fields": {
                "default_fields": {},
                "data_fields": {
                    "assignee": ["JRNewbie"],
                    "priority": "3",
                    "due": "2025-12-25",
                },
                "custom_fields": {"custom_field": "some_value"},
                "strict": False,
            },
            "original_text": "N/A",
        }
    ]
    for tag in result:
        convert_pep350_tag_to_TODO(tag)


def test_no_codetag_found():
    input_text = "x = y + 1 # This is just a regular comment"
    result = parse_codetags(input_text, PEP350Schema, strict=False)
    assert not result


def test_tag_with_mixed_fields():
    input_text = "# RFE: Add a new feature for exporting. <assignee:Micahe,CLE priority=1 2025-06-15>"
    result = parse_codetags(input_text, PEP350Schema, strict=False)
    assert result == [
        {
            "code_tag": "RFE",
            "comment": "Add a new feature for exporting.",
            "fields": {
                "default_fields": {
                    "origination_date": "2025-06-15",
                },
                "data_fields": {
                    "assignee": ["Micahe", "CLE"],
                    "priority": "1",
                    "origination_date": "2025-06-15",
                },
                "custom_fields": {},
                "strict": False,
            },
            "original_text": "N/A",
        }
    ]
    for tag in result:
        convert_pep350_tag_to_TODO(tag)


def test_tag_with_empty_field_block():
    input_text = "# NOTE: Remember to check performance. <>"
    result = parse_codetags(input_text, PEP350Schema, strict=False)
    assert result == [
        {
            "code_tag": "NOTE",
            "comment": "Remember to check performance.",
            "fields": {"default_fields": {}, "custom_fields": {}, "data_fields": {}, "strict": False},
            "original_text": "N/A",
        }
    ]
    for tag in result:
        convert_pep350_tag_to_TODO(tag)


def test_consecutive_tags_in_block():
    input_text = """
    # TODO: 1 <>
    # NOTE: 2 <>
    # RFE: 3 <>
    """
    result = parse_codetags(input_text, PEP350Schema, strict=False)
    empties = {"default_fields": {}, "data_fields": {}, "custom_fields": {}, "strict": False}
    assert result == [
        {"code_tag": "TODO", "comment": "1", "fields": empties, "original_text": "N/A"},
        {"code_tag": "NOTE", "comment": "2", "fields": empties, "original_text": "N/A"},
        {"code_tag": "RFE", "comment": "3", "fields": empties, "original_text": "N/A"},
    ]
    for tag in result:
        convert_pep350_tag_to_TODO(tag)


def test_tracker():
    input_text = """    # DONE: Basic screen buffer initialization completed. <Alice due=06/15/2024 release=1.0.0 category=Flavor Text status=Done tracker='https://example.com/FSH-2'>"""
    result = parse_codetags(input_text, PEP350Schema, strict=False)
    assert result[0]["fields"]["data_fields"]["tracker"] == "https://example.com/FSH-2"
    for tag in result:
        convert_pep350_tag_to_TODO(tag)


def test_many_example():
    example_comments = [
        "# FIXME: Seems like this Loop should be finite. <MDE, CLE d:14w p:2>",
        "while True: # BUG: Crashes if run on Sundays. <MDE 2005-09-04 d:2015-6-6 p:2>",  # Modified for user's test
        """
        # TODO: This is a complex task that needs more details.
        # <
        #   assignee=JRNewbie
        #   priority:3
        #   due=2025-12-25
        #   custom_field: some_value
        # >
        """,
        "x = y + 1 # This is just a regular comment",
        "# RFE: Add a new feature for exporting. <assignee:Micahe,CLE priority=1 2025-06-15>",  # User's assignee test
        "# NOTE: Remember to check performance. <>",
        """
        # TODO: 1 <>
        # NOTE: 2 <>
        # RFE: 3 <>
        """,
        """    # DONE: Basic screen buffer initialization completed. <Alice due=06/15/2024 release=1.0.0 category='Flavor Text' status=Done tracker='https://example.com/FSH-2'>""",
        # User's original test case, added quotes to category for robustness
    ]

    for i, comment in enumerate(example_comments):
        print(f"\nExample {i + 1}:")
        print("Input:", comment.strip())
        for result in parse_codetags(comment, PEP350Schema, strict=False):
            print("Output:", result)


def test_tracker_category():
    # Test cases from the problem description, refined with assert-like checks
    print("\n--- Specific Tracker and Assignee Tests ---")

    # Test for 'tracker' and 'category' from original query
    input_text_tracker = """    # DONE: Basic screen buffer initialization completed. <Alice due=06/15/2024 release=1.0.0 category='Flavor Text' status=Done tracker='https://example.com/FSH-2'>"""
    test_results_tracker = parse_codetags(input_text_tracker, PEP350Schema, strict=False)
    print("\nInput for Tracker/Category Test:", input_text_tracker.strip())
    print("Test Output for Tracker/Category:", test_results_tracker)
    assert (
        test_results_tracker
        and test_results_tracker[0]["fields"]["data_fields"].get("tracker") == "https://example.com/FSH-2"
    )

    assert test_results_tracker and test_results_tracker[0]["fields"]["data_fields"].get("category") == "Flavor Text"


def test_due_and_assignee():
    # Test for 'due' date parsing (d:2015-6-6)
    input_text_due = "while True: # BUG: Crashes if run on Sundays. <MDE 2005-09-04 d:2015-6-6 p:2>"
    test_results_due = parse_codetags(input_text_due, PEP350Schema, strict=False)
    print("\nInput for Due Date Test:", input_text_due.strip())
    print("Test Output for Due Date:", test_results_due)
    assert test_results_due and test_results_due[0]["fields"]["data_fields"].get("due") == "2015-6-6"

    assert test_results_due and test_results_due[0]["fields"]["default_fields"].get("assignee") == ["MDE"]


def test_assignee_and_date():
    # Test for assignee parsing (Micahe,CLE)
    input_text_assignee = "# RFE: Add a new feature for exporting. <assignee:Micahe,CLE priority=1 2025-06-15>"
    test_results_assignee = parse_codetags(input_text_assignee, PEP350Schema, strict=False)
    print("\nInput for Assignee Test:", input_text_assignee.strip())
    print("Test Output for Assignee:", test_results_assignee)
    assert test_results_assignee and test_results_assignee[0]["fields"]["data_fields"].get("assignee") == [
        "Micahe",
        "CLE",
    ]

    assert (
        test_results_assignee
        and test_results_assignee[0]["fields"]["default_fields"].get("origination_date") == "2025-06-15"
    )


def test_buggy_double():
    content = """
        # TODO: Implement collision detection for fish and tank walls. <Alice iteration=2 release_due=1.5.0 category=Fish Movement status=Development tracker=https://example.com/FSH-13>
        # TODO: Add food pellets for fish to eat. <Carl category=Flavor Text status=Planning iteration=2 tracker=https://example.com/FSH-14>
"""
    results = parse_codetags(content, PEP350Schema, strict=False)
    assert len(results) == 2


def test_buggy_double_round_trip():
    content = """
        # TODO: Implement collision detection for fish and tank walls. <Alice iteration=2 release_due=1.5.0 category='Fish Movement' status=Development tracker=https://example.com/FSH-13>
        # TODO: Add food pellets for fish to eat. <Carl category='Flavor Text' status=Planning iteration=2 tracker=https://example.com/FSH-14>
"""
    results = parse_codetags(content, PEP350Schema, strict=False)
    comment_again = [convert_pep350_tag_to_TODO(result) for result in results]
    final = [_.as_pep350_comment() for _ in comment_again]
    assert "Alice" in final[0]
    assert "Carl" in final[1]
