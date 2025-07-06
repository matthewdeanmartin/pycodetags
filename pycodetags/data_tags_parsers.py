"""
Parse specific schemas of data tags
"""

from __future__ import annotations

import logging
import re
from collections.abc import Generator
from pathlib import Path

from pycodetags import folk_tags_parser
from pycodetags.comment_finder import find_comment_blocks_from_string
from pycodetags.data_tags_methods import merge_two_dicts, promote_fields
from pycodetags.data_tags_schema import DataTag, DataTagFields, DataTagSchema
from pycodetags.exceptions import SchemaError
from pycodetags.folk_tags_schema import FolkTag

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # noqa

logger = logging.getLogger(__name__)


def iterate_comments_from_file(
    file: str, schemas: list[DataTagSchema], include_folk_tags: bool
) -> Generator[DataTag | FolkTag]:
    """
    Collect PEP-350 style code tags from a given file.

    Args:
        file (str): The path to the file to process.
        schemas (DataTaSchema): Schemas that will be detected in file
        include_folk_tags (bool): Include folk schemas that do not strictly follow PEP350

    Yields:
        PEP350Tag: A generator yielding PEP-350 style code tags found in the file.
    """
    logger.info(f"iterate_comments: processing {file}")
    yield from iterate_comments(Path(file).read_text(encoding="utf-8"), Path(file), schemas, include_folk_tags)


def iterate_comments(
    source: str, source_file: Path | None, schemas: list[DataTagSchema], include_folk_tags: bool
) -> Generator[DataTag | FolkTag]:
    """
    Collect PEP-350 style code tags from a given file.

    Args:
        source (str): The source text to process.
        source_file (Path): Where did the source come from
        schemas (DataTaSchema): Schemas that will be detected in file
        include_folk_tags (bool): Include folk schemas that do not strictly follow PEP350

    Yields:
        PEP350Tag: A generator yielding PEP-350 style code tags found in the file.
    """
    if not schemas and not include_folk_tags:
        raise SchemaError("No active schemas, not looking for folk tags. Won't find anything.")
    things: list[DataTag | FolkTag] = []
    for _start_line, _start_char, _end_line, _end_char, final_comment in find_comment_blocks_from_string(source):
        # Can only be one comment block now!
        logger.debug(f"Search for {[_['name'] for _ in schemas]} schema tags")
        found_data_tags = []
        for schema in schemas:
            found_data_tags = parse_codetags(final_comment, schema, strict=False)

            for found in found_data_tags:
                found["file_path"] = str(source_file) if source_file else None
                found["original_text"] = final_comment
                found["original_schema"] = "PEP350"
                found["offsets"] = (_start_line, _start_char, _end_line, _end_char)

            if found_data_tags:
                logger.debug(f"Found data tags! : {','.join(_['code_tag'] for _ in found_data_tags)}")
            things.extend(found_data_tags)

        for schema in schemas:
            if not found_data_tags and include_folk_tags and schema["matching_tags"]:
                # BUG: fails if there are two in the same. Blank out consumed text, reconsume bock <matth 2025-07-04
                #  category:parser priority:high status:development release:1.0.0 iteration:1>
                found_folk_tags: list[FolkTag] = []
                # TODO: support config of folk schema.<matth 2025-07-04 category:config priority:high status:development release:1.0.0 iteration:1>
                folk_tags_parser.process_text(
                    final_comment,
                    allow_multiline=True,
                    default_field_meaning="assignee",
                    found_tags=found_folk_tags,
                    file_path=str(source_file) if source_file else "",
                    valid_tags=schema["matching_tags"],
                )
                for found_folk_tag in found_folk_tags:
                    a, b, c, d = found_folk_tag["offsets"] or (0, 0, 0, 0)
                    new_offset = _start_line + a, _start_char + b, _end_line + c, _end_char + d
                    found_folk_tag["offsets"] = new_offset

                if found_folk_tags:
                    logger.debug(f"Found folk tags! : {','.join(_['code_tag'] for _ in found_folk_tags)}")
                things.extend(found_folk_tags)

    yield from things


def is_int(s: str) -> bool:
    """Check if a string can be interpreted as an integer.
    Args:
        s (str): The string to check.

    Returns:
        bool: True if the string is an integer, False otherwise.

    Examples:
        >>> is_int("123")
        True
        >>> is_int("-456")
        True
        >>> is_int("+789")
        True
        >>> is_int("12.3")
        False
        >>> is_int("abc")
        False
        >>> is_int("")
        False
    """
    if len(s) and s[0] in ("-", "+"):
        return s[1:].isdigit()
    return s.isdigit()


def parse_fields(
    field_string: str, schema: DataTagSchema, strict: bool  # pylint: disable=unused-argument
) -> DataTagFields:
    """
    Parse a field string from a PEP-350 style code tag and return a dictionary of fields.

    Args:
        field_string (str): The field string to parse.
        schema (DataTagSchema): The schema defining the fields and their aliases.
        strict: bool: If True, raises an error if a field appears in multiple places.

    Returns:
        Fields: A dictionary containing the parsed fields.
    """
    legit_names = {}
    for key in schema["data_fields"]:
        legit_names[key] = key
    field_aliases: dict[str, str] = merge_two_dicts(schema["data_field_aliases"], legit_names)

    fields: DataTagFields = {
        "default_fields": {},
        "data_fields": {},
        "custom_fields": {},
        "unprocessed_defaults": [],
        "identity_fields": [],
    }

    # Updated key_value_pattern:
    # - Handles quoted values (single or double) allowing any characters inside.
    # - For unquoted values, it now strictly matches one or more characters that are NOT:
    #   - whitespace `\s`
    #   - single quote `'`
    #   - double quote `"`
    #   - angle bracket `<` (which signals end of field string)
    #   - a comma `,` (unless it's part of a quoted string or explicitly for assignee splitting)
    #   The change here ensures it stops at whitespace, which correctly separates '1' from '2025-06-15'.
    key_value_pattern = re.compile(
        r"""
        ([a-zA-Z_][a-zA-Z0-9_]*) # Key (group 1): alphanumeric key name
        \s*[:=]\s* # Separator (colon or equals, with optional spaces)
        (                        # Start of value group (group 2)
            '(?:[^'\\]|\\.)*' |  # Match single-quoted string (non-greedy, allowing escaped quotes)
            "(?:[^"\\]|\\.)*" |  # Match double-quoted string (non-greedy, allowing escaped quotes)
            (?:[^\s'"<]+)       # Unquoted value: one or more characters not in \s ' " <
        )
        """,
        re.VERBOSE,  # Enable verbose regex for comments and whitespace
    )

    key_value_matches = []
    # Find all key-value pairs in the field_string
    for match in key_value_pattern.finditer(field_string):
        # Store the span (start, end indices) of the match, the key, and the raw value
        key_value_matches.append((match.span(), match.group(1), match.group(2)))

    # Process extracted key-value pairs
    for (_start_idx, _end_idx), key, value_raw in key_value_matches:
        key_lower = key.lower()

        # Strip quotes from the value if it was quoted
        value = value_raw
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        elif value.startswith('"') and value.endswith('"'):
            value = value[1:-1]

        # Assign the parsed value to the appropriate field
        if key_lower in field_aliases:
            normalized_key: str = field_aliases[key_lower]
            if normalized_key == "assignee":
                # Assignees can be comma-separated in unquoted values
                if "assignee" in fields["data_fields"]:
                    fields["data_fields"]["assignee"].extend([v.strip() for v in value.split(",") if v])
                else:
                    fields["data_fields"]["assignee"] = [v.strip() for v in value.split(",") if v]
            else:
                fields["data_fields"][normalized_key] = value
        else:
            # If not a predefined field, add to custom_fields
            fields["custom_fields"][key] = value

    # Extract remaining tokens that were not part of any key-value pair
    consumed_spans = sorted([span for span, _, _ in key_value_matches])

    unconsumed_segments = []
    current_idx = 0
    # Iterate through the field_string to find segments not covered by key-value matches
    for start, end in consumed_spans:
        if current_idx < start:
            # If there's a gap between the last consumed part and the current match, it's unconsumed
            segment = field_string[current_idx:start].strip()
            if segment:  # Only add non-empty segments
                unconsumed_segments.append(segment)
        current_idx = max(current_idx, end)  # Move current_idx past the current consumed area

    # Add any remaining part of the string after the last key-value match
    if current_idx < len(field_string):
        segment = field_string[current_idx:].strip()
        if segment:  # Only add non-empty segments
            unconsumed_segments.append(segment)

    # Join the unconsumed segments and then split by whitespace to get individual tokens
    other_tokens_raw = " ".join(unconsumed_segments)
    other_tokens = [token.strip() for token in other_tokens_raw.split() if token.strip()]

    # Process these remaining tokens for dates (origination_date) and assignees (initials)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")

    # This is too domain specific. Let a plugin handle user aliases.
    # initials_pattern = re.compile(r"^[A-Z,]+$")  # Matches comma-separated uppercase initials

    for token in other_tokens:
        # handles this case:
        # <foo:bar
        #   fizz:buzz
        #  bing:bong>
        if token == "#":  # nosec
            continue
        matched_default = False

        # for default_type, default_key in schema["default_fields"].items():
        # str must go last, it matches everything!
        matched_default = False
        for default_type in ["int", "date", "str", "str|list[str]"]:
            default_key = schema["default_fields"].get(default_type)
            if default_key:
                # Default fields!
                if not matched_default:
                    if default_type == "date" and date_pattern.match(token):
                        # Assign default_key from a standalone date token
                        fields["default_fields"][default_key] = token  # type: ignore[assignment]
                        matched_default = True
                    elif default_type.replace(" ", "") == "str|list[str]":  # initials_pattern.match(token):
                        # Add standalone initials to assignees list
                        if default_key in fields["default_fields"]:
                            fields["default_fields"][default_key].extend([t.strip() for t in token.split(",") if t])
                        else:
                            fields["default_fields"][default_key] = [t.strip() for t in token.split(",") if t]
                        matched_default = True
                    elif default_type == "int" and is_int(token):
                        fields["default_fields"][default_key] = token  # type: ignore[assignment]
                        matched_default = True
                    elif default_type == "str":
                        fields["default_fields"][default_key] = token  # type: ignore[assignment]
                        matched_default = True

        if not matched_default:
            fields["unprocessed_defaults"].append(token)

    return fields


def parse_codetags(text_block: str, data_tag_schema: DataTagSchema, strict: bool) -> list[DataTag]:
    """
    Parse PEP-350 style code tags from a block of text.

    Args:
        text_block (str): The block of text containing PEP-350 style code tags.
        data_tag_schema: DataTagSchema: The schema defining the fields and their aliases.
        strict: bool: If True, raises an error if a field appears in multiple places.

    Returns:
        list[PEP350Tag]: A list of PEP-350 style code tags found in the text block.
    """
    results: list[DataTag] = []
    code_tag_regex = re.compile(
        r"""
        (?P<code_tag>[A-Z\?\!]{3,}) # Code tag (e.g., TODO, FIXME, BUG)
        \s*:\s* # Colon separator with optional whitespace
        (?P<comment>.*?)            # Comment text (non-greedy)
        <                           # Opening angle bracket for fields
        (?P<field_string>.*?)       # Field string (non-greedy)
        >                           # Closing angle bracket for fields
        """,
        re.DOTALL | re.VERBOSE,  # DOTALL allows . to match newlines, VERBOSE allows comments in regex
    )

    matches = list(code_tag_regex.finditer(text_block))
    for match in matches:
        tag_parts = {
            "code_tag": match.group("code_tag").strip(),
            "comment": match.group("comment").strip().rstrip(" \n#"),  # Clean up comment
            "field_string": match.group("field_string")
            .strip()
            .replace("\n", " "),  # Replace newlines in fields with spaces
        }
        fields = parse_fields(tag_parts["field_string"], data_tag_schema, strict)
        results.append(
            {
                "code_tag": tag_parts["code_tag"],
                "comment": tag_parts["comment"],
                "fields": fields,
                "original_text": "N/A",  # BUG: Regex doesn't allow for showing this! <matth 2025-07-04
                # category:parser priority:high status:development release:1.0.0 iteration:1>
            }
        )

    # promote standard fields in custom_fields to root, merging if already exist
    for result in results:
        promote_fields(result, data_tag_schema)
    return results
