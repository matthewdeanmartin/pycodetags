"""
Schema for codetags that represent developer discussion, intended
for lightweight annotation, threading, and possible synchronization
with external platforms like Mastodon.
"""

from pycodetags import DataTagSchema

DiscussionTagSchema: DataTagSchema = {
    "name": "discussion",
    "matching_tags": ["QUESTION", "ANSWER", "CHAT", "POST", "COMMENT", "DISCUSSION"],
    "default_fields": {
        "str": "author",
        "date": "date",
    },
    "data_fields": {
        # Comment is the status text.
        "author": "str",  # Author initials or handle
        "date": "str",  # ISO 8601 string
        "tags": "list[str]",  # Optional list of topic tags
        "mastodon_id": "str",  # URL or ID of the toot
        "in_reply_to": "str",  # ID of the question or message being answered
        "spoiler_text": "str",  # Optional text for spoiler warnings
        "thread_id": "str",  # Optional identifier for a discussion thread
        "language": "str",  # Optional language code
        "idempotency_key": "str",
    },
    "data_field_aliases": {
        "a": "author",
        "d": "date",
        "t": "tags",
        "m": "mastodon_id",
        "r": "in_reply_to",
        "s": "spoiler_text",
        "tid": "thread_id",
        "l": "language",
        "ik": "idempotency_key",
    },
}
