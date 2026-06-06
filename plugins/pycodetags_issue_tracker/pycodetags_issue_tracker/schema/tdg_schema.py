"""
TDG schema (ribtoks/tdg-github-action comment format).

A TDG tag is a multi-line comment:

    # TODO: This is the title of the issue to create
    # category=SomeCategory issue=123 estimate=30m author=alias
    # This is a multiline description of the issue
    # that will be in the "Body" property of the comment

Line 1 is the type + title, line 2 (optional) is a space-separated ``key=value`` property line, and
the remaining ``#`` lines are the body. The ``issue=NNN`` field links a tag to a GitHub issue and is
treated as the tag's identity when present.

See ``spec/id_and_tdg.md`` Part 3.
"""

from __future__ import annotations

from pycodetags.data_tags.data_tags_schema import DataTagSchema

TDGSchema: DataTagSchema = {
    "name": "TDG",
    "matching_tags": ["TODO", "FIXME", "BUG", "HACK"],
    "default_fields": {},
    "data_fields": {
        "title": "str",
        "body": "str",
        "category": "str",
        "issue": "int",  # GitHub issue number -> tracker identity
        "estimate": "float",  # hours
        "author": "str",
        "id": "int",  # local identity, shared concept with the issue tracker schema
    },
    "data_field_aliases": {
        "cat": "category",
    },
    "field_infos": {},
    # When a TDG tag carries an issue number, that number IS its identity. Otherwise identity falls
    # back to code_tag + comment (the title).
    "identity_fields": ["issue"],
}
