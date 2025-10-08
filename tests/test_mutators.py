"""
Unit tests for the pycodetags.mutator module.
These tests use pytest and do not mock file system operations.
"""

import pytest
from pathlib import Path
from typing import List

from pycodetags.common_interfaces import string_to_data
# These imports assume the pycodetags package structure.
# You may need to adjust them based on your project setup.
from pycodetags.mutator import (
    apply_mutations,
    delete_tags,
    replace_with_strings,
    insert_tags,
)
from pycodetags.data_tags import DATA
from pycodetags.exceptions import DataTagError

# --- Test Data and Fixtures ---

SAMPLE_CODE_SIMPLE = """
import os

# TODO: Refactor this function <user:matt status:pending>
def old_function():
    pass

# FIXME: This is a critical bug <id:123 priority:high>
def broken_function():
    return False
"""

SAMPLE_CODE_MULTILINE = """
class ComplexClass:
    # TODO: This is a complex, multi-line
    # comment that needs to be handled correctly.
    # <author:alice priority:low>
    def __init__(self):
        self.value = 1

    def another_method(self):
        # BUG: A simple one-liner bug <ticket:456>
        return self.value * 2
"""

BLANK_LINES_CODE = """def function_one():
    pass



def function_two():
    pass
"""


@pytest.fixture
def source_file(tmp_path: Path) -> Path:
    """Fixture to create a simple source file for testing."""
    p = tmp_path / "test_module.py"
    p.write_text(SAMPLE_CODE_SIMPLE)
    return p


@pytest.fixture
def multiline_source_file(tmp_path: Path) -> Path:
    """Fixture to create a source file with multi-line comments."""
    p = tmp_path / "multiline_module.py"
    p.write_text(SAMPLE_CODE_MULTILINE)
    return p


@pytest.fixture
def blank_lines_file(tmp_path: Path) -> Path:
    """Fixture to create a source file with blank lines for insertion."""
    p = tmp_path / "blank_lines_module.py"
    p.write_text(BLANK_LINES_CODE)
    return p


# --- Tests for apply_mutations (Core Logic) ---

def test_update_single_tag(source_file: Path):
    """Test updating a single tag to a new state."""
    tags = list(string_to_data(source_file.read_text(), file_path=source_file))
    todo_tag = tags[0]
    assert todo_tag.code_tag == "TODO"

    # Create the new state for the tag
    new_tag = DATA(
        code_tag="TODO",
        comment="This function has been refactored",
        data_fields={"user": "matt", "status": "done"},
    )

    apply_mutations(source_file, [(todo_tag, new_tag)])

    expected_content = """
import os

# TODO: This function has been refactored <user:matt status:done>
def old_function():
    pass

# FIXME: This is a critical bug <id:123 priority:high>
def broken_function():
    return False
"""
    assert source_file.read_text() == expected_content


def test_remove_single_tag(source_file: Path):
    """Test removing a single tag."""
    tags = list(string_to_data(source_file.read_text(), file_path=source_file))
    fixme_tag = tags[1]
    assert fixme_tag.code_tag == "FIXME"

    apply_mutations(source_file, [(fixme_tag, None)])

    expected_content = """
import os

# TODO: Refactor this function <user:matt status:pending>
def old_function():
    pass


def broken_function():
    return False
"""
    # Note: The removal might leave an extra newline, which is acceptable.
    # We can use strip() to make the comparison more robust if needed.
    assert source_file.read_text().replace("\n\n\n", "\n\n") == expected_content.replace("\n\n\n", "\n\n")


def test_update_and_remove_multiple_tags(source_file: Path):
    """Test a mixed operation of updating one tag and removing another."""
    tags = list(string_to_data(source_file.read_text(), file_path=source_file))
    todo_tag, fixme_tag = tags

    new_todo_tag = DATA(code_tag="DONE", comment="Refactoring complete")

    # The order in the list shouldn't matter due to internal sorting
    mutations = [(fixme_tag, None), (todo_tag, new_todo_tag)]
    apply_mutations(source_file, mutations)

    expected_content = """
import os

# DONE: Refactoring complete <>
def old_function():
    pass


def broken_function():
    return False
"""
    assert source_file.read_text().replace("\n\n\n", "\n\n") == expected_content.replace("\n\n\n", "\n\n")


def test_update_multiline_tag(multiline_source_file: Path):
    """Test updating a multi-line tag, which changes its line count."""
    tags = list(string_to_data(multiline_source_file.read_text(), file_path=multiline_source_file))
    multiline_todo = tags[0]

    new_tag = DATA(
        code_tag="REFACTORED",
        comment="Init is now simplified.",
        data_fields={"author": "alice", "status": "complete"},
    )

    apply_mutations(multiline_source_file, [(multiline_todo, new_tag)])

    expected_content = """
class ComplexClass:
    # REFACTORED: Init is now simplified. <author:alice status:complete>
    def __init__(self):
        self.value = 1

    def another_method(self):
        # BUG: A simple one-liner bug <ticket:456>
        return self.value * 2
"""
    assert multiline_source_file.read_text() == expected_content


def test_remove_multiline_tag(multiline_source_file: Path):
    """Test removing a multi-line tag."""
    tags = list(string_to_data(multiline_source_file.read_text(), file_path=multiline_source_file))
    multiline_todo = tags[0]

    apply_mutations(multiline_source_file, [(multiline_todo, None)])

    expected_content = """
class ComplexClass:
    
    def __init__(self):
        self.value = 1

    def another_method(self):
        # BUG: A simple one-liner bug <ticket:456>
        return self.value * 2
"""
    # Stripping leading/trailing whitespace to handle file-end nuances
    assert multiline_source_file.read_text().strip() == expected_content.strip()


def test_error_on_externally_modified_file(source_file: Path):
    """Test that DataTagError is raised if file is modified after parsing."""
    tags = list(string_to_data(source_file.read_text(), file_path=source_file))
    todo_tag = tags[0]

    # Modify the file *after* parsing
    source_file.write_text("This file has been completely changed.")

    with pytest.raises(DataTagError, match="Tag mismatch"):
        apply_mutations(source_file, [(todo_tag, None)])


def test_error_on_nonexistent_file(tmp_path: Path):
    """Test that FileNotFoundError is raised."""
    non_existent_path = tmp_path / "ghost.py"
    dummy_tag = DATA(
        original_text="# DUMMY", offsets=(0, 0, 0, 8)
    )  # Dummy tag for the call
    with pytest.raises(FileNotFoundError):
        apply_mutations(non_existent_path, [(dummy_tag, None)])


# --- Tests for Syntactic Sugar Functions ---

def test_delete_tags(source_file: Path):
    """Test the delete_tags convenience function."""
    tags = list(string_to_data(source_file.read_text(), file_path=source_file))

    delete_tags(source_file, tags)  # Delete all tags

    expected_content = """
import os


def old_function():
    pass


def broken_function():
    return False
"""
    # Use split and join to normalize multiple newlines for robust comparison
    assert "\n".join(s for s in source_file.read_text().split("\n") if s.strip()) == "\n".join(
        s for s in expected_content.split("\n") if s.strip())


def test_replace_with_strings(source_file: Path):
    """Test the replace_with_strings convenience function."""
    tags = list(string_to_data(source_file.read_text(), file_path=source_file))
    todo_tag, fixme_tag = tags

    replacements = [
        (todo_tag, "This is a new TODO comment."),
        (fixme_tag, "This is a new FIXME comment."),
    ]
    replace_with_strings(source_file, replacements)

    expected_content = """
import os

# TODO: This is a new TODO comment. <>
def old_function():
    pass

# FIXME: This is a new FIXME comment. <>
def broken_function():
    return False
"""
    assert source_file.read_text() == expected_content


# --- Tests for insert_tags ---

def test_insert_single_tag(blank_lines_file: Path):
    """Test inserting one tag into a blank line."""
    tag_to_insert = DATA(code_tag="NOTE", comment="Adding a new function here soon.")

    # Insert on line 4 (1-based), which is blank
    insert_tags(blank_lines_file, [(4, tag_to_insert, 4)])

    expected_content = """def function_one():
    pass

    # NOTE: Adding a new function here soon. <>


def function_two():
    pass
"""
    assert blank_lines_file.read_text() == expected_content


def test_insert_multiple_tags(blank_lines_file: Path):
    """Test inserting multiple tags in descending order."""
    tag1 = DATA(code_tag="INFO", comment="First insertion.")
    tag2 = DATA(code_tag="INFO", comment="Second insertion.")

    # Insert on lines 3 and 5
    insert_tags(blank_lines_file, [(3, tag1, 0), (5, tag2, 0)])

    expected_content = """def function_one():
    pass
# INFO: First insertion. <>


# INFO: Second insertion. <>

def function_two():
    pass
"""
    assert blank_lines_file.read_text() == expected_content


def test_insert_at_end_of_file(blank_lines_file: Path):
    """Test inserting a tag after the last line of code."""
    tag = DATA(code_tag="FINAL", comment="End of module.")
    num_lines = len(blank_lines_file.read_text().splitlines())

    # Insert on the line after the last one
    insert_tags(blank_lines_file, [(num_lines + 1, tag, 0)])

    # Read and check that the new tag is at the end
    content = blank_lines_file.read_text()
    assert "# FINAL: End of module. <>" in content.splitlines()[-1]


def test_insert_error_on_non_blank_line(blank_lines_file: Path):
    """Test that inserting on a non-blank line raises a ValueError."""
    tag = DATA(code_tag="FAIL", comment="This should not work.")
    with pytest.raises(ValueError, match="Line is not blank"):
        insert_tags(blank_lines_file, [(1, tag, 0)])  # Line 1 has code


def test_insert_error_on_out_of_bounds_line(blank_lines_file: Path):
    """Test that inserting on an out-of-bounds line number raises ValueError."""
    tag = DATA(code_tag="FAIL", comment="This should not work.")
    with pytest.raises(ValueError, match="Invalid line number"):
        insert_tags(blank_lines_file, [(100, tag, 0)])

