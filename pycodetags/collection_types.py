from __future__ import annotations

try:
    from typing import TypedDict  # noqa: F401
except ImportError:
    from typing_extensions import TypedDict

from pycodetags import TODO, TodoException


class CollectedTODOs(TypedDict, total=False):
    """TypedDict for collected TODOs, Dones, and exceptions."""

    todos: list[TODO]
    exceptions: list[TodoException]
