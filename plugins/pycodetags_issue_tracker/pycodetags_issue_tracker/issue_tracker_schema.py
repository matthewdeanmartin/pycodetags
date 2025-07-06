from __future__ import annotations

from pycodetags.data_tags_schema import DataTagSchema

IssueTrackerSchema: DataTagSchema = {
    "name": "TODO",
    "matching_tags": [
        "TODO",
        "REQUIREMENT",
        "STORY",
        "IDEA",
        # Defects
        "FIXME",
        "BUG",
        # Negative sentiment
        "HACK",
        "CLEVER",
        "MAGIC",
        "ALERT",
        # Categories of tasks
        "PORT",
        "DOCUMENT",
    ],
    "default_fields": {"str": "originator", "date": "origination_date"},
    "data_fields": {
        "priority": "str",  # or str | int?
        "due": "date",
        "tracker": "str",
        "status": "str",
        "category": "str",
        "iteration": "str",  # or str | int?
        "release": "str",  # or str | int | version?
        "assignee": "str",  # or str | list[str]?
        "originator": "str",  # who created the issue
        "origination_date": "date",  # when the issue was created
        "closed_date": "date",  # when the issue was closed
        "change_type": "str",  # e.g. 'Added', 'Changed', 'Deprecated', 'Removed', 'Fixed', 'Security'
    },
    "data_field_aliases": {
        "p": "priority",
        "d": "due",
        "t": "tracker",
        "s": "status",
        "c": "category",
        "i": "iteration",
        "r": "release",
        "a": "assignee",
    },
}
