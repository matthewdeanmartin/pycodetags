"""Shared title/body and metadata handling for explicitly selected TDG and extended PEP-350."""

from __future__ import annotations

import ast
import io
import json
import re
from typing import TYPE_CHECKING

from pycodetags.data_tags.data_tags_schema import DataTagSchema
from pycodetags.exceptions import DataTagParseError, SchemaError
from pycodetags.python.comment_finder import extract_comment_lines

if TYPE_CHECKING:
    from pycodetags.data_tags.data_tags_classes import DATA

ANCHOR = re.compile(r"^[ \t]*#[ \t]*([A-Z][A-Z0-9_!?]*)[ \t]*:[ \t]*(.*)$")
PREFIX = re.compile(r"^[ \t]*#[ \t]?")
KEY = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*([=:])\s*")
SINGLE_QUOTED = re.compile(r"'(?:[^'\\]|\\.)*'", re.DOTALL)


def parse_properties(text: str, schema: DataTagSchema, positional: bool = False) -> dict[str, str]:
    """Parse complete metadata, including escaped quotes; reject duplicate or incomplete fields.

    PEP-350 permits positional author/date shorthand. All other properties are named. Values remain
    strings so parsing neither coerces user input nor evaluates schema defaults.
    """
    result: dict[str, str] = {}
    authors = []
    cursor = 0
    while cursor < len(text):
        if text[cursor].isspace():
            cursor += 1
            continue
        match = KEY.match(text, cursor)
        if not match:
            if not positional:
                raise DataTagParseError(f"Expected key=value metadata near {text[cursor:]!r}.")
            token = text[cursor:].split()[0]
            cursor += len(token)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
                key, value = "origination_date", token
            elif re.fullmatch(r"[\w.,@+-]+", token):
                authors.append(token)
                continue
            else:
                raise DataTagParseError(f"Invalid positional metadata {token!r}; use a named property.")
        else:
            key = match[1].lower()
            if schema["format"] == "TDG" and match[2] != "=":
                raise DataTagParseError("TDG properties use key=value.")
            cursor = match.end()
            if cursor == len(text):
                raise DataTagParseError(f'Missing value for {key!r}; quote an empty value as "".')
            try:
                if text[cursor] == '"':
                    value, length = json.JSONDecoder().raw_decode(text[cursor:])
                    cursor += length
                elif text[cursor] == "'":
                    quoted = SINGLE_QUOTED.match(text, cursor)
                    if not quoted:
                        raise ValueError("Unterminated string")
                    value = ast.literal_eval(quoted[0])
                    cursor = quoted.end()
                else:
                    value = text[cursor:].split()[0]
                    cursor += len(value)
            except (ValueError, SyntaxError) as error:
                raise DataTagParseError(f"Invalid quoted value for {key!r}.") from error
            if cursor < len(text) and not text[cursor].isspace():
                raise DataTagParseError(f"Expected whitespace after {key!r}.")
        key = schema.get("data_field_aliases", {}).get(key, key)
        if key in ("title", "body"):
            raise DataTagParseError(f"{key} belongs in comment text, not metadata.")
        if key in result:
            raise DataTagParseError(f"Duplicate property {key!r}.")
        result[key] = value
    if authors:
        if "author" in result:
            raise DataTagParseError("Author supplied both positionally and by name.")
        result["author"] = " ".join(authors)
    return result


def property_line(text: str) -> bool:
    """A TDG metadata line begins with an assignment; prose containing an assignment stays body."""
    match = KEY.match(text.lstrip())
    return bool(match and match[2] == "=")


def split_pep_metadata(text: str) -> tuple[str, str] | None:
    """Find a trailing bracket block independently of literal angle brackets in the narrative."""
    candidates = [index for index, char in enumerate(text) if char == "<"]
    for start in reversed(candidates):
        backslashes = len(text[:start]) - len(text[:start].rstrip("\\"))
        if backslashes % 2:
            continue
        line_start = text.rfind("\n", 0, start) + 1
        if line_start and text[line_start:].startswith("\\"):
            continue
        quote = None
        escaped = False
        for index in range(start + 1, len(text)):
            char = text[index]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char in ("'", '"'):
                if quote is None:
                    quote = char
                elif quote == char:
                    quote = None
            if quote is not None:
                continue
            if char == "<":
                break
            if char == ">":
                if text[index + 1 :].strip():
                    break
                prefix = text[:start]
                if "\n" in prefix and not prefix.rsplit("\n", 1)[1].strip():
                    prefix = prefix.rsplit("\n", 1)[0]
                else:
                    prefix = prefix.rstrip(" \t")
                return prefix, text[start + 1 : index]
    return None


def unescape_body(line: str) -> str:
    """A leading backslash makes a syntax-like body line literal."""
    return line[1:] if line.startswith("\\") else line


def parse_block(source: str, schema: DataTagSchema) -> list[dict]:
    """Parse a comment block using exactly one selected format, in source order."""
    raw_lines = io.StringIO(source).readlines()
    lines = [line.rstrip("\r\n") for line in raw_lines]
    anchors = [(index, ANCHOR.match(line)) for index, line in enumerate(lines)]
    anchors = [(index, match) for index, match in anchors if match and match[1] in schema["matching_tags"]]
    tags = []
    for position, (start, match) in enumerate(anchors):
        stop = anchors[position + 1][0] if position + 1 < len(anchors) else len(lines)
        # A standalone parser may also receive executable lines; they terminate a comment tag.
        for index in range(start + 1, stop):
            if not PREFIX.match(lines[index]):
                stop = index
                break
        title = match[2]
        body_lines = [PREFIX.sub("", line, count=1) for line in lines[start + 1 : stop]]
        if schema["format"] == "TDG":
            properties = (
                parse_properties(body_lines.pop(0), schema) if body_lines and property_line(body_lines[0]) else {}
            )
        else:
            narrative_lines = [title] + body_lines
            split = None
            for count, line in enumerate(narrative_lines, 1):
                if line.rstrip().endswith(">"):
                    split = split_pep_metadata("\n".join(narrative_lines[:count]))
                    if split is not None:
                        stop = start + count
                        break
            if split is None:
                if any(line.lstrip().startswith("<") for line in body_lines):
                    raise DataTagParseError("Unterminated PEP-350 metadata block.")
                continue
            narrative, metadata = split
            title, *body_lines = narrative.split("\n")
            title = re.sub(r"\\([\\<])", r"\1", title)
            properties = parse_properties(metadata, schema, positional=True)
        fields = {
            "data_fields": {key: value for key, value in properties.items() if key in schema["data_fields"]},
            "custom_fields": {key: value for key, value in properties.items() if key not in schema["data_fields"]},
            "default_fields": {},
            "unprocessed_defaults": [],
            "identity_fields": schema.get("identity_fields", []),
        }
        offsets = (start, lines[start].index("#"), stop - 1, len(lines[stop - 1]))
        tags.append(
            {
                "code_tag": match[1],
                "comment": title.strip(),
                "title": title.strip(),
                "body": "\n".join(unescape_body(line) for line in body_lines),
                "fields": fields,
                "original_schema": schema["name"],
                "original_text": extract_comment_lines(raw_lines, offsets),
                "offsets": offsets,
            }
        )
    return tags


def quote_value(value: object) -> str:
    """Keep simple values readable; JSON quoting preserves empty strings, slashes, and quotes."""
    text = str(value)
    if not text or any(char.isspace() or char in "\\\"'<>" for char in text):
        return json.dumps(text, ensure_ascii=False)
    return text


def serialize_tag(tag: DATA, schema: DataTagSchema) -> str:
    """Render either format from one record, without wrapping titles or discarding body whitespace."""
    code_tag = tag.code_tag or ""
    if code_tag not in schema["matching_tags"]:
        raise SchemaError(f"Tag {code_tag!r} is not recognized by schema {schema['name']!r}.")
    title = tag.title if tag.title is not None else (tag.comment or "")
    if "\n" in title or "\r" in title:
        raise DataTagParseError("A title must be one line; put additional lines in body.")
    properties = {}
    for field_set in (tag.default_fields, tag.custom_fields, tag.data_fields):
        for key, value in (field_set or {}).items():
            key = schema.get("data_field_aliases", {}).get(key, key)
            if key in properties and properties[key] != value:
                raise DataTagParseError(f"Conflicting values for {key!r}.")
            if key not in ("title", "body", "id") and value is not None:
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key):
                    raise DataTagParseError(f"Invalid property name {key!r}.")
                properties[key] = value
    # Canonical typed id takes priority over legacy field dictionaries.
    local_id = tag.tag_id
    if local_id is None:
        local_id = (tag.data_fields or {}).get("id", (tag.custom_fields or {}).get("id"))
    if local_id is not None:
        properties["id"] = local_id
    metadata = " ".join(f"{key}={quote_value(value)}" for key, value in properties.items())
    body = []
    if tag.body:
        for line in tag.body.split("\n"):
            anchor = ANCHOR.match("# " + line)
            if (
                line.startswith("\\")
                or (anchor and anchor[1] in schema["matching_tags"])
                or "<" in line
                or property_line(line)
            ):
                line = "\\" + line
            body.append("# " + line)
    if schema["format"] == "PEP350":
        title = title.replace("\\", "\\\\").replace("<", "\\<")
    out = [f"# {code_tag}: {title}"]
    if schema["format"] == "TDG":
        if metadata:
            out.append("# " + metadata)
        out.extend(body)
    else:
        out.extend(body)
        if body:
            out.append(f"# <{metadata}>")
        else:
            out[0] += f" <{metadata}>"
    return "\n".join(out)
