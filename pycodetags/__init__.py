"""
Code Tags is a tool and library for putting TODOs into source code.

Only the strongly typed decorators, exceptions and context managers are exported.

Everything else is a tool.
"""

__all__ = [
    "TODO",
    "FIXME",
    "TodoException",
    "REQUIREMENT",
    "STORY",
    "IDEA",
    "BUG",
    "HACK",
    "CLEVER",
    "MAGIC",
    "ALERT",
    "PORT",
    "DOCUMENT",
]

from pycodetags.todo_tag_types import TODO, TodoException
from pycodetags.todo_tag_types_aliases import (
    ALERT,
    BUG,
    CLEVER,
    DOCUMENT,
    FIXME,
    HACK,
    IDEA,
    MAGIC,
    PORT,
    REQUIREMENT,
    STORY,
)
