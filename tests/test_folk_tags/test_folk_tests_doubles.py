# import pytest
#
# from pycodetags.folk_tags_parser import FolkTag, process_line
#
#
# @pytest.fixture
# def temp_file(tmp_path):
#     """Fixture to create a temporary file for testing."""
#
#     def _create_file(filename, content):
#         file_path = tmp_path / filename
#         file_path.write_text(content)
#         return str(file_path)
#
#     return _create_file
#
#
# ## Tests for find_source_tags
#
#
# def test_find_source_tags_single_file_no_duplicates(temp_file):
#     """
#     Test that find_source_tags processes a single file without
#     detecting the same tag twice.
#     """
#     code = """
# # TODO: First comment
# # BUG: Another comment
# # TODO: Third comment
# """
#     file_path = temp_file("test_file_no_duplicates.py", code)
#
#     tags = find_source_tags(file_path, valid_tags=["TODO", "BUG"])
#
#     assert len(tags) == 3
#     assert tags[0]["comment"] == "First comment"
#     assert tags[1]["comment"] == "Another comment"
#     assert tags[2]["comment"] == "Third comment"
#     assert len({(t["line_number"], t["comment"]) for t in tags}) == 3  # Ensure unique line/comment combinations
#
#
# def test_find_source_tags_multiline_no_duplicates(temp_file):
#     """
#     Test multiline comments to ensure they are treated as a single tag
#     and not duplicated.
#     """
#     code = """
# # TODO: Multiline
# # comment line 2
# # comment line 3
# # BUG: Single line bug
# """
#     file_path = temp_file("test_multiline.py", code)
#
#     tags = find_source_tags(file_path, valid_tags=["TODO", "BUG"], allow_multiline=True)
#
#     assert len(tags) == 2
#     assert tags[0]["comment"] == "Multiline comment line 2 comment line 3"
#     assert tags[0]["line_number"] == 2  # First line of the multiline comment
#     assert tags[1]["comment"] == "Single line bug"
#
#
# def test_find_source_tags_consecutive_same_tag(temp_file):
#     """
#     Test consecutive tags of the same type to ensure each is detected.
#     """
#     code = """
# # TODO: First task
# # TODO: Second task
# # TODO: Third task
# """
#     file_path = temp_file("test_consecutive_tags.py", code)
#
#     tags = find_source_tags(file_path, valid_tags=["TODO"])
#
#     assert len(tags) == 3
#     assert tags[0]["comment"] == "First task"
#     assert tags[1]["comment"] == "Second task"
#     assert tags[2]["comment"] == "Third task"
#     assert len({(t["line_number"], t["comment"]) for t in tags}) == 3
#
#
# def test_find_source_tags_overlapping_tags_single_line(temp_file):
#     """
#     Test a scenario where a comment might look like a tag but isn't,
#     or tags are closely spaced.
#     """
#     code = """
# # TODO: Actual todo
# # This is not a tag
# # ANOTHER: Another tag
# # TODO(user): Specific todo
# """
#     file_path = temp_file("test_overlapping_tags.py", code)
#
#     tags = find_source_tags(file_path, valid_tags=["TODO", "ANOTHER"])
#
#     assert len(tags) == 3
#     assert tags[0]["comment"] == "Actual todo"
#     assert tags[0]["line_number"] == 2
#     assert tags[1]["comment"] == "Another tag"
#     assert tags[1]["line_number"] == 4
#     assert tags[2]["comment"] == "Specific todo"
#     assert tags[2]["line_number"] == 5
#     assert len({(t["line_number"], t["comment"]) for t in tags}) == 3
#
#
# def test_find_source_tags_empty_file(temp_file):
#     """Test with an empty file."""
#     file_path = temp_file("empty.py", "")
#     tags = find_source_tags(file_path, valid_tags=["TODO"])
#     assert len(tags) == 0
#
#
# def test_find_source_tags_file_with_no_tags(temp_file):
#     """Test with a file containing no folk tags."""
#     code = """
# def some_function():
#     pass
# # Just a regular comment
# # This is also a comment, but not a folk tag
# """
#     file_path = temp_file("no_tags.py", code)
#     tags = find_source_tags(file_path, valid_tags=["TODO"])
#     assert len(tags) == 0
#
#
# def test_find_source_tags_file_with_invalid_tags(temp_file):
#     """Test that only valid tags are parsed when `valid_tags` is provided."""
#     code = """
# # TODO: Valid todo
# # FIXIT: Invalid fixme
# # BUG: Valid bug
# """
#     file_path = temp_file("invalid_tags.py", code)
#     tags = find_source_tags(file_path, valid_tags=["TODO", "BUG"])
#
#     assert len(tags) == 2
#     comments = {tag["comment"] for tag in tags}
#     assert "Valid todo" in comments
#     assert "Valid bug" in comments
#     assert "Invalid fixme" not in comments
#
#
# def test_find_source_tags_default_field_meaning(temp_file):
#     """Test that default_field_meaning correctly assigns the default field."""
#     code = """
# # TODO(john.doe): Fix this issue
# # REVIEW(jane.smith): Review this code
# """
#     file_path = temp_file("default_field.py", code)
#
#     tags_assignee = find_source_tags(file_path, valid_tags=["TODO", "REVIEW"], default_field_meaning="assignee")
#     assert len(tags_assignee) == 2
#     assert tags_assignee[0].get("assignee") == "john.doe"
#     assert tags_assignee[1].get("assignee") == "jane.smith"
#
#     tags_person = find_source_tags(file_path, valid_tags=["TODO", "REVIEW"], default_field_meaning="person")
#     assert len(tags_person) == 2
#     assert tags_person[0].get("person") == "john.doe"
#     assert tags_person[1].get("person") == "jane.smith"
#
#
# def test_find_source_tags_complex_comment_formats(temp_file):
#     """Test various comment formats including custom fields and URLs."""
#     code = """
# # TODO(user): Update docs.domain.com/ticket-123 This is a comment.
# # BUG(qa=tester, priority=high): Fix critical bug in module.
# # FIXME: Some fix without fields.
# # HACK(originator): Some temporary solution.
# """
#     file_path = temp_file("complex_comments.py", code)
#     tags = find_source_tags(file_path, valid_tags=["TODO", "BUG", "FIXME", "HACK"], default_field_meaning="originator")
#
#     assert len(tags) == 4
#
#     # TODO tag
#     assert tags[0]["code_tag"] == "TODO"
#     assert tags[0]["default_field"] == "user"
#     assert tags[0]["comment"] == "Update docs.domain.com/ticket-123 This is a comment."
#     assert tags[0]["tracker"] == "docs.domain.com/ticket-123"
#     assert tags[0]["original_text"] == "(user): Update docs.domain.com/ticket-123 This is a comment."
#     assert tags[0]["originator"] == "user"  # because default_field_meaning is originator
#
#     # BUG tag
#     assert tags[1]["code_tag"] == "BUG"
#     assert tags[1]["custom_fields"] == {"qa": "tester", "priority": "high"}
#     assert tags[1]["comment"] == "Fix critical bug in module."
#
#     # FIXME tag
#     assert tags[2]["code_tag"] == "FIXME"
#     assert tags[2]["default_field"] is None
#     assert not tags[2]["custom_fields"]
#     assert tags[2]["comment"] == "Some fix without fields."
#
#     # HACK tag
#     assert tags[3]["code_tag"] == "HACK"
#     assert tags[3]["default_field"] == "originator"
#     assert tags[3]["originator"] == "originator"
#
#
# def test_find_source_tags_multiline_with_fields(temp_file):
#     """Test multiline comments with fields."""
#     code = """
# # TODO(assignee=me):
# #   This is a multiline comment
# #   that continues on.
# """
#     file_path = temp_file("multiline_with_fields.py", code)
#     tags = find_source_tags(file_path, valid_tags=["TODO"], allow_multiline=True)
#
#     assert len(tags) == 1
#     assert tags[0]["code_tag"] == "TODO"
#     assert tags[0]["custom_fields"] == {"assignee": "me"}
#     assert tags[0]["comment"] == "This is a multiline comment that continues on."
#     assert tags[0]["line_number"] == 2
#
#
# ## Tests for process_line (internal function, but good for focused testing)
#
#
# def test_process_line_basic_tag():
#     found_tags: list[FolkTag] = []
#     lines = ["# TODO: Do something"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["TODO"], False, "assignee")
#     assert consumed == 1
#     assert len(found_tags) == 1
#     assert found_tags[0]["comment"] == "Do something"
#     assert found_tags[0]["code_tag"] == "TODO"
#
#
# def test_process_line_multiline_tag():
#     found_tags: list[FolkTag] = []
#     lines = ["# FIXME: Line 1", "# Line 2", "# Line 3"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["FIXME"], True, "assignee")
#     assert consumed == 3
#     assert len(found_tags) == 1
#     assert found_tags[0]["comment"] == "Line 1 Line 2 Line 3"
#     assert found_tags[0]["code_tag"] == "FIXME"
#
#
# def test_process_line_multiline_tag_stops_at_next_tag():
#     found_tags: list[FolkTag] = []
#     lines = ["# TODO: First part", "# Second part", "# BUG: This is a new bug"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["TODO", "BUG"], True, "assignee")
#     assert consumed == 2  # Consumes only the TODO and its continuation
#     assert len(found_tags) == 1
#     assert found_tags[0]["comment"] == "First part Second part"
#     assert found_tags[0]["code_tag"] == "TODO"
#
#     # Now process the next line, which should be the BUG
#     found_tags_bug: list[FolkTag] = []
#     consumed_bug = process_line("test.py", found_tags_bug, lines, consumed, ["TODO", "BUG"], True, "assignee")
#     assert consumed_bug == 1
#     assert len(found_tags_bug) == 1
#     assert found_tags_bug[0]["comment"] == "This is a new bug"
#     assert found_tags_bug[0]["code_tag"] == "BUG"
#
#
# def test_process_line_no_tag_on_line():
#     found_tags: list[FolkTag] = []
#     lines = ["# Just a comment"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["TODO"], False, "assignee")
#     assert consumed == 1
#     assert len(found_tags) == 0  # No tag should be found if it's not a valid_tag
#
#
# def test_process_line_multiline_without_allow_multiline():
#     found_tags: list[FolkTag] = []
#     lines = ["# TODO: First part", "# Second part"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["TODO"], False, "assignee")
#     assert consumed == 1  # Only the first line should be consumed
#     assert len(found_tags) == 1
#     assert found_tags[0]["comment"] == "First part"
#
#     # The second line would be processed as a separate line by the outer loop if it were a valid tag.
#     # In this case, it's just a regular comment and shouldn't be picked up.
#     found_tags_second_line: list[FolkTag] = []
#     consumed_second = process_line("test.py", found_tags_second_line, lines, 1, ["TODO"], False, "assignee")
#     assert consumed_second == 1
#     assert len(found_tags_second_line) == 0
#
#
# def test_process_line_with_default_field_meaning_person():
#     found_tags: list[FolkTag] = []
#     lines = ["# TODO(Alice): implement feature"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["TODO"], False, "person")
#     assert consumed == 1
#     assert len(found_tags) == 1
#     assert found_tags[0].get("person") == "Alice"
#     assert found_tags[0]["default_field"] == "Alice"
#
#
# def test_process_line_with_multiple_default_fields():
#     found_tags: list[FolkTag] = []
#     lines = ["# TODO(Alice, Bob): review code"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["TODO"], False, "assignee")
#     assert consumed == 1
#     assert len(found_tags) == 1
#     assert found_tags[0].get("assignee") == "Alice, Bob"
#     assert found_tags[0]["default_field"] == "Alice, Bob"
#
#
# def test_process_line_with_custom_fields():
#     found_tags: list[FolkTag] = []
#     lines = ["# TODO(module=auth, ticket=XYZ-123): fix login"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["TODO"], False, "assignee")
#     assert consumed == 1
#     assert len(found_tags) == 1
#     assert found_tags[0]["custom_fields"] == {"module": "auth", "ticket": "XYZ-123"}
#     assert found_tags[0]["comment"] == "fix login"
#
#
# def test_process_line_with_tracker_url():
#     found_tags: list[FolkTag] = []
#     lines = ["# BUG: Fix bug at example.com/bug-report"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["BUG"], False, "assignee")
#     assert consumed == 1
#     assert len(found_tags) == 1
#     assert found_tags[0]["tracker"] == "example.com/bug-report"
#
#
# def test_process_line_with_colon_after_tag():
#     found_tags: list[FolkTag] = []
#     lines = ["# TODO: This has a colon"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["TODO"], False, "assignee")
#     assert consumed == 1
#     assert len(found_tags) == 1
#     assert found_tags[0]["comment"] == "This has a colon"
#
#     found_tags_no_colon: list[FolkTag] = []
#     lines_no_colon = ["# TODO This has no colon"]
#     consumed_no_colon = process_line("test.py", found_tags_no_colon, lines_no_colon, 0, ["TODO"], False, "assignee")
#     assert consumed_no_colon == 1
#     assert len(found_tags_no_colon) == 1
#     assert found_tags_no_colon[0]["comment"] == "This has no colon"  # Should still work
#
#
# def test_process_line_with_numeric_id():
#     found_tags: list[FolkTag] = []
#     lines = ["# FIXME 12345: This is a ticket ID"]
#     consumed = process_line("test.py", found_tags, lines, 0, ["FIXME"], False, "assignee")
#     assert consumed == 1
#     assert len(found_tags) == 1
#     assert found_tags[0]["default_field"] == "12345"
#     assert found_tags[0]["comment"] == "This is a ticket ID"
#
#
# def test_process_line_multiline_with_empty_lines_and_non_comment_lines(temp_file):
#     """
#     Test multiline comments with interleaved empty lines or lines that are not comments
#     to ensure they terminate correctly.
#     """
#     code = """
# # TODO: Multiline
# # comment line 2
#
# # This is a regular code line
# # comment line 3 (should not be part of the above TODO)
# """
#     file_path = temp_file("test_multiline_breaks.py", code)
#
#     tags = find_source_tags(file_path, valid_tags=["TODO"], allow_multiline=True)
#
#     assert len(tags) == 1
#     assert tags[0]["comment"] == "Multiline comment line 2"
#     assert tags[0]["line_number"] == 2
