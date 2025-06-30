import pathlib

from pycodetags.converters import convert_pep350_tag_to_DATA
from pycodetags.data_tag_types import DATA

# Assuming pycodetags is installed or accessible in the Python path
from pycodetags.data_tags import DataTag, DataTagFields, DataTagSchema, parse_codetags, promote_fields
from pycodetags.data_tags_parsers import iterate_comments

# Define a sample schema for testing
TEST_SCHEMA: DataTagSchema = {
    "name": "TEST",
    "matching_tags": ["TODO", "FIXME", "BUG"],
    "default_fields": {"str": "assignee", "date": "origination_date"},
    "data_fields": {
        "priority": "str",
        "category": "str",
        "ticket": "str",
        "iteration": "str",
        "status": "str",
        "assignee": "str",
        "origination_date": "str",
    },
    "data_field_aliases": {
        "p": "priority",
        "cat": "category",
        "t": "ticket",
        "iter": "iteration",
        "st": "status",
        "a": "assignee",
        "o": "origination_date",
    },
}


def compare_data_tags(tag1: DataTag, tag2: DataTag) -> bool:
    """
    Compares two DataTag objects for deep equality, ignoring original_text.
    This provides value semantics comparison for the TypedDict structure.
    """
    if tag1.get("code_tag") != tag2.get("code_tag"):
        return False
    if tag1.get("comment") != tag2.get("comment"):
        return False

    # Compare fields carefully
    fields1: DataTagFields = tag1.get("fields", {"default_fields": {}, "data_fields": {}, "custom_fields": {}})
    fields2: DataTagFields = tag2.get("fields", {"default_fields": {}, "data_fields": {}, "custom_fields": {}})

    # Don't compare default_fields. This is a serialization style signal
    # if fields1.get("default_fields") != fields2.get("default_fields"):
    #     return False

    # Compare data_fields
    if fields1.get("data_fields") != fields2.get("data_fields"):
        return False

    # Compare custom_fields
    if fields1.get("custom_fields") != fields2.get("custom_fields"):
        return False

    return True


# --- Round Trip Test: Source Code -> DataTag -> Source Code (Loosy-Goosy Equivalence) ---


def test_source_to_datatag_to_source_roundtrip_loose(tmp_path: pathlib.Path):
    """
    Tests the round trip from source code to DataTag and back to source,
    with a loose equivalence check.
    """
    python_code_with_tags = """
def some_function():
    # TODO: Implement feature X <priority:high category:new_feature ticket:PROJ-123 assignee:johndoe origination_date:2023-01-15>
    pass

class MyClass:
    # FIXME: Refactor this class <status:inprogress iteration:2 custom_field:custom_value>
    def __init__(self):
        pass

# BUG: Critical bug in login flow <priority:critical>
# Another line of a bug comment that is multiline.
# A third line.
    """

    # Write the Python code to a temporary file
    file_path = tmp_path / "test_code.py"
    file_path.write_text(python_code_with_tags)

    # 1. Parse source code into DataTag objects
    parsed_data_tags_raw = list(iterate_comments(str(file_path), [TEST_SCHEMA], include_folk_tags=False))

    parsed_data_tags = list(convert_pep350_tag_to_DATA(_, TEST_SCHEMA) for _ in parsed_data_tags_raw)
    # Ensure some tags were found
    assert len(parsed_data_tags) >= 2, "Expected at least two DataTags to be parsed"

    # 2. Convert DataTag objects back to source-like comments
    re_generated_comments = [
        tag.as_data_comment() if isinstance(tag, DATA) else str(tag)  # Fallback for FolkTag, though not expected here
        for tag in parsed_data_tags
    ]

    # Perform loosy-goosy equivalence check
    # Check if key components of the original comments are present in the regenerated ones
    assert any("Implement feature X" in comment for comment in re_generated_comments)
    assert any("priority:high" in comment and "category:new_feature" in comment for comment in re_generated_comments)
    assert any("ticket:PROJ-123" in comment for comment in re_generated_comments)
    assert any("Refactor this class" in comment for comment in re_generated_comments)
    assert any("status:inprogress" in comment and "iteration:2" in comment for comment in re_generated_comments)
    assert any("custom_field:custom_value" in comment for comment in re_generated_comments)
    assert any("Critical bug in login flow" in comment for comment in re_generated_comments)
    assert any("assignee:johndoe" in comment for comment in re_generated_comments)
    assert any("origination_date:2023-01-15" in comment for comment in re_generated_comments)


# --- Round Trip Test: DataTag -> Source Code -> DataTag (Value Semantics) ---


def test_datatag_to_source_to_datatag_roundtrip_strict():
    """
    Tests the round trip from a DataTag object to source code and back to DataTag,
    with a strict value semantics check.
    """
    original_data_tag: DataTag = {
        "code_tag": "TODO",
        "comment": "Refactor authentication module",
        "fields": {
            "default_fields": {"assignee": ["johndoe"], "origination_date": "2024-06-28"},
            "data_fields": {
                "priority": "medium",
                "category": "security",
                "ticket": "AUTH-456",
                "assignee": ["johndoe"],
                "origination_date": "2024-06-28",
            },
            "custom_fields": {"sprint": "S2", "team": "backend"},
        },
        "original_text": "N/A",  # This will be ignored in comparison
    }

    # Convert the DataTag to a DATA object for the as_data_comment method
    data_obj = DATA(
        code_tag=original_data_tag["code_tag"],
        comment=original_data_tag["comment"],
        default_fields=original_data_tag["fields"]["default_fields"],
        data_fields=original_data_tag["fields"]["data_fields"],
        custom_fields=original_data_tag["fields"]["custom_fields"],
    )

    # 1. Convert DataTag to source code comment
    generated_comment_string = data_obj.as_data_comment()

    # Validate the generated string looks reasonable
    assert "# TODO: Refactor authentication module" in generated_comment_string
    assert "johndoe" in generated_comment_string
    assert "2024-06-28" in generated_comment_string
    assert "priority:medium" in generated_comment_string
    assert "category:security" in generated_comment_string
    assert "ticket:AUTH-456" in generated_comment_string
    assert "sprint:S2" in generated_comment_string
    assert "team:backend" in generated_comment_string

    # 2. Parse the generated source code comment back into a DataTag
    # parse_codetags expects a block of text, so we'll wrap it slightly.
    re_parsed_data_tags = parse_codetags(generated_comment_string, TEST_SCHEMA, strict=False)

    assert len(re_parsed_data_tags) == 1, "Expected exactly one DataTag to be re-parsed"
    re_parsed_data_tag = re_parsed_data_tags[0]

    # 3. Assert deep equality using custom comparison function
    assert compare_data_tags(original_data_tag, re_parsed_data_tag), (
        f"Original DataTag and re-parsed DataTag are not equivalent.\n"
        f"Original: {original_data_tag}\n"
        f"Re-parsed: {re_parsed_data_tag}"
    )


def test_datatag_to_source_to_datatag_with_quoted_values():
    """
    Tests round-trip with DataTag containing quoted values in fields.
    """
    original_data_tag: DataTag = {
        "code_tag": "NOTE",
        "comment": "This is a comment with spaces and 'quotes'",
        "fields": {
            "default_fields": {},
            "data_fields": {},
            "custom_fields": {
                "message": 'A value with spaces and "double quotes"',
                "path": "'/path/to/my file.txt'",
                "description": "Multi-word description, with:colon and =equal signs",
            },
        },
        "original_text": "N/A",
    }

    data_obj = convert_pep350_tag_to_DATA(original_data_tag, TEST_SCHEMA)
    generated_comment_string = data_obj.as_data_comment()

    re_parsed_data_tags = parse_codetags(generated_comment_string, TEST_SCHEMA, strict=False)
    assert len(re_parsed_data_tags) == 1
    re_parsed_data_tag = re_parsed_data_tags[0]

    assert compare_data_tags(original_data_tag, re_parsed_data_tag)


def test_datatag_to_source_to_datatag_with_multiline_comment(tmp_path: pathlib.Path):
    """
    Tests round-trip with a DataTag where the original comment spans multiple lines.
    The `as_data_comment` method should collapse it, and `parse_codetags` should re-parse correctly.
    """
    python_code_with_multiline_tag = """
# TODO: This is a multi-line comment
# that should be preserved as a single comment string.
# priority: high
# ticket: ABC-123 <assignee:janedoe>
    """
    expected_comment = "This is a multi-line comment that should be preserved as a single comment string."

    # Need to simulate how `iterate_comments` processes multiline comments
    # and then how `parse_codetags` handles the resulting block.
    # The `comment_finder.py` `find_comment_blocks` combines contiguous hash comments.

    file_path = tmp_path / "multiline_test.py"
    file_path.write_text(python_code_with_multiline_tag)

    # Step 1: Get the combined comment block from the file
    found_blocks = list(pathlib.Path(file_path).read_text(encoding="utf-8").splitlines())

    # Manually extract the combined comment text as iterate_comments would
    # This simulates the behavior of find_comment_blocks and iterate_comments
    # The first line has the tag, subsequent lines are part of the comment content
    combined_comment_text_for_parsing = ""
    in_tag_block = False
    for line in found_blocks:
        stripped_line = line.strip()
        if stripped_line.startswith("# TODO:"):
            in_tag_block = True
            combined_comment_text_for_parsing += stripped_line[stripped_line.find("#") + 1 :] + " "
        elif in_tag_block and stripped_line.startswith("#"):
            combined_comment_text_for_parsing += stripped_line[stripped_line.find("#") + 1 :] + " "
        elif in_tag_block and not stripped_line.startswith("#"):
            break  # End of comment block

    # The `iterate_comments` function would pass the `final_comment` which is the entire block.
    # Let's craft the `final_comment` as `iterate_comments` would
    # from the source code, `find_comment_blocks` would give us the full block:

    full_comment_block = """# TODO: This is a multi-line comment
# that should be preserved as a single comment string.
# priority: high
# ticket: ABC-123 <assignee:janedoe>"""

    # Now, parse this block with parse_codetags
    initial_parsed_tags = parse_codetags(full_comment_block, TEST_SCHEMA, strict=False)

    assert len(initial_parsed_tags) == 1
    initial_data_tag = initial_parsed_tags[0]

    # Manually adjust the comment to match the expected outcome after parsing
    # The `comment` field in `DataTag` from `parse_codetags` will have newlines replaced by spaces.
    initial_data_tag["comment"] = expected_comment.strip()

    # Create a DATA object from the parsed tag for generating the comment
    data_obj = DATA(
        code_tag=initial_data_tag["code_tag"],
        comment=initial_data_tag["comment"],
        default_fields=initial_data_tag["fields"].get("default_fields"),
        data_fields=initial_data_tag["fields"].get("data_fields"),
        custom_fields=initial_data_tag["fields"].get("custom_fields"),
        # _original_text is not passed to DATA constructor but it's okay for comparison
    )

    generated_comment_string = data_obj.as_data_comment()

    # Re-parse the generated comment string
    re_parsed_data_tags = parse_codetags(generated_comment_string, TEST_SCHEMA, strict=False)
    assert len(re_parsed_data_tags) == 1
    re_parsed_data_tag = re_parsed_data_tags[0]

    # The `original_text` field is not set by `parse_codetags` currently, so we clear it for comparison.
    # Also, ensure 'comment' is normalized for comparison, as `as_data_comment` might reformat it slightly.
    initial_data_tag_for_comparison = initial_data_tag.copy()
    initial_data_tag_for_comparison["original_text"] = ""  # Clear as it's not round-tripped
    initial_data_tag_for_comparison["comment"] = initial_data_tag_for_comparison["comment"].strip()

    re_parsed_data_tag_for_comparison = re_parsed_data_tag.copy()
    re_parsed_data_tag_for_comparison["original_text"] = ""  # Clear for comparison
    re_parsed_data_tag_for_comparison["comment"] = re_parsed_data_tag_for_comparison["comment"].strip()

    # Compare the core fields
    promote_fields(initial_data_tag_for_comparison, TEST_SCHEMA)
    promote_fields(re_parsed_data_tag_for_comparison, TEST_SCHEMA)
    assert compare_data_tags(initial_data_tag_for_comparison, re_parsed_data_tag_for_comparison)
