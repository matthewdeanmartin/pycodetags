"""
Parse specific schemas of data tags
"""

from __future__ import annotations

import logging
import re
from collections.abc import Generator
from pathlib import Path

from pycodetags.data_tags import folk_tags_parser
from pycodetags.data_tags.data_tags_methods import DataTag, merge_two_dicts, promote_fields
from pycodetags.data_tags.data_tags_schema import DataTagFields, DataTagSchema
from pycodetags.exceptions import SchemaError
from pycodetags.python.comment_finder import find_comment_blocks_from_string

logger = logging.getLogger(__name__)


__all__ = ["iterate_comments_from_file", "iterate_comments"]


def iterate_comments_from_file(file: str, schemas: list[DataTagSchema], include_folk_tags: bool) -> Generator[DataTag]:
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


def _extend_to_comment_prefix(block: str, line_start: int, match_start: int) -> int:
    """Move ``match_start`` left over a leading ``#``/whitespace prefix on its block line.

    A normal tag is written ``# TODO: ...``; the regex matches from the ``T``, but the text we want to
    rewrite (and report as ``original_text``) includes the ``# `` prefix. We only extend when the gap
    between the line start and the match is *only* whitespace and ``#`` characters -- so a second tag
    sharing a physical line (``... <p:1> FIXME: ...``) is NOT extended over the preceding tag's text.
    """
    prefix = block[line_start:match_start]
    if prefix.strip(" \t#") == "":
        # The comment line's own indentation/`#` -- include from the first `#`.
        hash_idx = prefix.find("#")
        if hash_idx != -1:
            return line_start + hash_idx
    return match_start


def _span_to_offsets(
    block: str, span: tuple[int, int], block_start_line: int, block_start_char: int
) -> tuple[tuple[int, int, int, int], str]:
    """Convert a block-relative char ``span`` to absolute file offsets + the per-tag substring.

    The block string's first line is sliced at ``block_start_char`` in the source, so a column on that
    first line must be shifted by ``block_start_char``; later lines are full source lines, so their
    columns are already absolute (spec/id_and_tdg.md §7.3.5).
    """
    raw_start, end = span
    # Start of the block-line that contains raw_start.
    line_start = block.rfind("\n", 0, raw_start) + 1  # 0 if no newline before
    start = _extend_to_comment_prefix(block, line_start, raw_start)

    def to_abs(char_index: int) -> tuple[int, int]:
        dline = block.count("\n", 0, char_index)
        cur_line_start = block.rfind("\n", 0, char_index) + 1
        col = char_index - cur_line_start
        if dline == 0:
            col += block_start_char
        return block_start_line + dline, col

    start_line, start_char = to_abs(start)
    end_line, end_char = to_abs(end)
    return (start_line, start_char, end_line, end_char), block[start:end]


def iterate_comments(
    source: str, source_file: Path | None, schemas: list[DataTagSchema], include_folk_tags: bool
) -> Generator[DataTag]:
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
    things: list[DataTag] = []
    for _start_line, _start_char, _end_line, _end_char, final_comment in find_comment_blocks_from_string(source):
        # Can only be one comment block now!
        logger.debug(f"Search for {[_['name'] for _ in schemas]} schema tags")
        found_data_tags = []
        for schema in schemas:
            tags_with_spans = parse_codetags_with_spans(final_comment, schema, strict=False)
            found_data_tags = [tag for tag, _ in tags_with_spans]

            for found, span in tags_with_spans:
                found["file_path"] = str(source_file) if source_file else None
                found["original_schema"] = "PEP350"
                # Per-tag offsets/original_text from each match's block span, so multiple tags in one
                # comment block do not all claim the whole block (spec/id_and_tdg.md Part 7).
                offsets, original_text = _span_to_offsets(final_comment, span, _start_line, _start_char)
                found["offsets"] = offsets
                found["original_text"] = original_text

            if found_data_tags:
                logger.debug(f"Found data tags! : {','.join(_['code_tag'] for _ in found_data_tags)}")
            things.extend(found_data_tags)

        for schema in schemas:
            if not found_data_tags and include_folk_tags and schema["matching_tags"]:
                # BUG: fails if there are two in the same. Blank out consumed text, reconsume bock <matth 2025-07-04
                #  category:parser priority:high status:development release:1.0.0 iteration:1>
                found_folk_tags: list[DataTag] = []
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
                    # BUG: Offsets here are buggy. <matth 2025-07-04 category:config priority:high status:development release:1.0.0>
                    a, b, c, d = found_folk_tag["offsets"] or (0, 0, 0, 0)
                    new_offset = _start_line + a, _start_char + b, _end_line + c, _end_char + d
                    found_folk_tag["offsets"] = new_offset

                if found_folk_tags:
                    logger.debug(f"Found folk tags! : {','.join(_['code_tag'] for _ in found_folk_tags)}")
                things.extend(found_folk_tags)

        # TDG pass: only for TDG-named schemas, only when PEP-350 found nothing in this block.
        # PEP-350 wins; TDG is the fallback. Imported here to avoid an import cycle.
        if not found_data_tags:
            from pycodetags.data_tags import tdg_tags_parser

            for schema in schemas:
                if schema.get("name") != "TDG":
                    continue
                for tdg_tag in tdg_tags_parser.iterate_comments(final_comment, source_file, [schema]):
                    a, b, c, d = tdg_tag["offsets"] or (0, 0, 0, 0)
                    # The block string's first line is sliced at _start_char, so its in-block char
                    # offset is relative to that; later lines are full source lines, so their char
                    # offset is already absolute.
                    abs_start_char = _start_char + b if a == 0 else b
                    tdg_tag["offsets"] = (_start_line + a, abs_start_char, _start_line + c, d)
                    things.append(tdg_tag)

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
            # TODO: handle assignee/ str|list[str] catdogs in a more general fashion <matth 2025-07-13 status=inprogress category=catdogs priority=high release=1.0.0>
            # if normalized_key == "assignee":
            #     # Assignees can be comma-separated in unquoted values
            #     if "assignee" in fields["data_fields"]:
            #         fields["data_fields"]["assignee"].extend([v.strip() for v in value.split(",") if v])
            #     else:
            #         fields["data_fields"]["assignee"] = [v.strip() for v in value.split(",") if v]
            # else:
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


_CODE_TAG_REGEX = re.compile(
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


def parse_codetags_with_spans(
    text_block: str, data_tag_schema: DataTagSchema, strict: bool
) -> list[tuple[DataTag, tuple[int, int]]]:
    """Parse PEP-350 tags and return each with its block-relative ``(start, end)`` char span.

    The span (start of the ``code_tag`` through the closing ``>``) lets callers compute *per-tag*
    offsets so multiple tags in one comment block do not all claim the whole block
    (spec/id_and_tdg.md Part 7). This is the internal worker; :func:`parse_codetags` is the public
    shape and does not expose spans.
    """
    results: list[tuple[DataTag, tuple[int, int]]] = []
    for match in _CODE_TAG_REGEX.finditer(text_block):
        tag_parts = {
            "code_tag": match.group("code_tag").strip(),
            "comment": match.group("comment").strip().rstrip(" \n#"),  # Clean up comment
            "field_string": match.group("field_string")
            .strip()
            .replace("\n", " "),  # Replace newlines in fields with spaces
        }
        fields = parse_fields(tag_parts["field_string"], data_tag_schema, strict)
        tag: DataTag = {
            "code_tag": tag_parts["code_tag"],
            "comment": tag_parts["comment"],
            "fields": fields,
            "original_text": "N/A",  # Overwritten per-tag by iterate_comments when from a file.
        }
        promote_fields(tag, data_tag_schema)
        results.append((tag, match.span()))
    return results


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
    return [tag for tag, _span in parse_codetags_with_spans(text_block, data_tag_schema, strict)]
