"""
Abstract data serialization format, of which PEP-350 is one schema.

In scope:
    - parsing a data tag as a data serialization format.
    - defining a schema
    - domain free concepts
    - Parsing python to extract # comments, be it AST or regex or other strategy
    - Round tripping to and from data tag format
    - Equivalence checking by value
    - Merging and promoting fields among default, data and custom.

Out of scope:
    - File system interation
    - Any particular schema (PEP350 code tags, discussion tags, documentation tags, etc)
    - Domain specific concepts (users, initials, start dates, etc)
    - Docstring style comments and docstrings

Inputs:
    - A block of valid python comment text
    - A schema

Outputs:
    - A python data structure that represents a data structure

Half-hearted goal:
    - Minimize python concepts so this can be implemented in Javascript, etc.
"""

from __future__ import annotations

import logging
import re
from typing import Any

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict # noqa

logger = logging.getLogger(__name__)


class DataTagSchema(TypedDict):
    default_fields: dict[str, str]
    """type:name, e.g. str:assignees"""

    data_fields: dict[str, str]
    """name:type, e.g. priority:str"""

    data_field_aliases: dict[str, str]
    """name:alias, e.g. priority:p"""


class DataTagFields(TypedDict):
    # When deserializating a field value could appear in default, data and custom field positions.
    default_fields: dict[str, list[Any]]
    """Field without label identified by data type, range or fallback, e.g. user and date"""

    # TODO: support dict[str, int | date | str | list[int, date, str]] ?
    data_fields: dict[str, Any]
    """Expected fields with labels, e.g. category, priority"""

    custom_fields: dict[str, str]
    """Key value pairs, e.g. SAFe program increment number"""

    # TODO: think about adding meaning of default fields here?

    strict: bool
    """If true, the same field can't appear in two places"""


def get_data_field_value(schema: DataTagSchema, fields: DataTagFields, field_name: str) -> Any:
    values = []
    # default fields should already be resolved to a data_field by this point
    if field_name in schema["data_fields"]:
        if field_name in fields["data_fields"]:
            values.append(fields["data_fields"][field_name])
        if field_name in fields["custom_fields"]:
            values.append(fields["custom_fields"][field_name])
    if len(set(values)) == 1:
        return values[0]
    if fields["strict"]:
        raise TypeError(f"Double field with different values {field_name} : {values}")
    logger.warning(f"Double field with different values {field_name} : {values}")
    # TODO: do we want to support str | list[str]?
    if values:
        return values[0]
    return ""


class DataTag(TypedDict, total=False):
    """An abstract data code tag."""

    code_tag: str
    comment: str
    fields: DataTagFields

    # metadata
    original_text: str


def promote_fields(tag: DataTag, data_tag_schema: DataTagSchema) -> None:
    fields = tag["fields"]
    if not fields.get("custom_fields", {}) and not fields.get("default_fields", {}):
        # nothing to promote
        return

    # It is already there, just move it over.
    for default_key, default_value in tag["fields"]["default_fields"].items():
        if default_key in fields["data_fields"] and fields["data_fields"][default_key] != default_value:
            # Strict?
            logger.warning(
                "Field in both data_fields and default_fields and they don't match: "
                f'{default_key}: {fields["data_fields"][default_key]} != {default_value}'
            )
            if isinstance(fields["data_fields"][default_key], list) and isinstance(default_value, list):
                fields["data_fields"][default_key].extend(default_value)
            elif isinstance(fields["data_fields"][default_key], list) and isinstance(default_value, str):
                fields["data_fields"][default_key].append(default_value)
            elif isinstance(fields["data_fields"][default_key], str) and isinstance(default_value, list):
                fields["data_fields"][default_key] = default_value + [fields["data_fields"][default_key]]
            elif isinstance(fields["data_fields"][default_key], str) and isinstance(default_value, str):
                # promotes str to list[str], ugly!
                fields["data_fields"][default_key] = [fields["data_fields"][default_key], default_value]

        else:
            fields["data_fields"][default_key] = default_value

    # promote a custom_field to root field if it should have been a root field.
    field_aliases: dict[str, str] = data_tag_schema["data_field_aliases"]
    # putative custom field, is it actually standard?
    for custom_field, custom_value in fields["custom_fields"].copy().items():
        if custom_field in field_aliases:
            # Okay, found a custom field that should have been standard
            full_alias = field_aliases[custom_field]

            if fields["data_fields"][full_alias]:
                # found something already there
                consumed = False
                if isinstance(fields["data_fields"][full_alias], list):
                    # root is list
                    if isinstance(custom_value, list):
                        # both are list: merge list into parent list
                        fields["data_fields"][full_alias].extend(custom_value)
                        consumed = True
                    elif isinstance(custom_value, str):
                        # list/string promote parent string to list (ugh!)
                        fields["data_fields"][full_alias] = fields["data_fields"][full_alias].append(custom_value)
                        consumed = True
                    else:
                        # list/surprise
                        logger.warning(f"Promoting custom_field {full_alias}/{custom_value} to unexpected type")
                        fields["data_fields"][full_alias].append(custom_value)
                        consumed = True
                elif isinstance(fields["data_fields"][full_alias], str):
                    if isinstance(custom_value, list):
                        # str/list: parent str joins custom list
                        fields["data_fields"][full_alias] = [fields["data_fields"][full_alias]] + custom_value
                        consumed = True
                    elif isinstance(custom_value, str):
                        # str/str forms a list
                        fields["data_fields"][full_alias] = [fields["data_fields"][full_alias], custom_value]
                        consumed = True
                    else:
                        # str/surprise
                        logger.warning(f"Promoting custom_field {full_alias}/{custom_value} to unexpected type")
                        fields["data_fields"][full_alias] = [
                            fields["data_fields"][full_alias],
                            custom_value,
                        ]  # xtype: ignore
                        consumed = True
                else:
                    # surprise/surprise = > list
                    logger.warning(f"Promoting custom_field {full_alias}/{custom_value} to unexpected type")
                    fields[full_alias] = [fields[full_alias], custom_value]  # type: ignore
                    consumed = True
                if consumed:
                    del fields["custom_fields"][custom_field]
                else:
                    # This might not  be reachable.
                    logger.warning(f"Failed to promote custom_field {full_alias}/{custom_value}, not consumed")


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


def parse_fields(field_string: str, schema: DataTagSchema, strict: bool) -> DataTagFields:
    """
    Parse a field string from a PEP-350 style code tag and return a dictionary of fields.

    Args:
        field_string (str): The field string to parse.
        schema (DataTagSchema): The schema defining the fields and their aliases.
        strict: bool: If True, raises an error if a field appears in multiple places.

    Returns:
        Fields: A dictionary containing the parsed fields.
    """
    field_aliases: dict[str, str] = merge_two_dicts(schema["data_field_aliases"], schema["data_fields"])

    fields: DataTagFields = {"default_fields": {}, "data_fields": {}, "custom_fields": {}, "strict": strict}

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
        for default_type in ["int", "date", "str"]:
            default_key = schema["default_fields"].get(default_type)
            if default_key:
                if not matched_default:
                    # Default fields!
                    if default_type == "date" and date_pattern.match(token):
                        # Assign default_key from a standalone date token
                        fields["default_fields"][default_key] = token  # type: ignore[assignment]
                        matched_default = True
                    elif default_type == "str":  # initials_pattern.match(token):
                        # Add standalone initials to assignees list
                        if default_key in fields["default_fields"]:
                            fields["default_fields"][default_key].extend([t.strip() for t in token.split(",") if t])
                        else:
                            fields["default_fields"][default_key] = [t.strip() for t in token.split(",") if t]
                        matched_default = True
                    elif default_type == "int" and is_int(token):
                        fields["default_fields"][default_key] = token  # type: ignore[assignment]
                        matched_default = True

    # TODO: promote default fields to data_fields
    return fields


def merge_two_dicts(x: dict[str, Any], y: dict[str, Any]) -> dict[str, Any]:
    z = x.copy()  # start with keys and values of x
    z.update(y)  # modifies z with keys and values of y
    return z


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
                "original_text": "N/A",  # BUG: Regex doesn't allow for showing this!
            }
        )

    # promote standard fields in custom_fields to root, merging if already exist
    for result in results:
        promote_fields(result, data_tag_schema)
    return results
