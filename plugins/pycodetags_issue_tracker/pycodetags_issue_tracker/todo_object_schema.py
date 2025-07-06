"""
Extract to break cyclical import
"""

from __future__ import annotations

TODO_KEYWORDS = [
    # People
    "assignee",
    "originator",
    # Dates
    "origination_date",
    "due",
    "closed_date",
    # Version number
    "release_due",
    "release",
    # keepachangelog field, done fields
    "change_type",
    # integration fields
    "tracker",
    # custom workflow fields
    # Source Mapping
    "file_path",
    "line_number",
    "offsets",
    "custom_fields",
    # Idiosyncratic fields
    "iteration",
    "priority",
    "status",
    "category",
]
