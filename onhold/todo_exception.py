"""
Strongly typed code tag types.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Callable, cast  # noqa

try:
    from typing import Literal  # type:ignore[assignment,unused-ignore]
except ImportError:
    from typing_extensions import Literal  # type:ignore[assignment,unused-ignore] # noqa


logger = logging.getLogger(__name__)


class TodoException(Exception):
    """Exception raised when a required feature is not implemented."""

    def __init__(self, message: str, assignee: str | None = None, due: str | None = None):
        super().__init__(message)
        self.assignee = assignee
        self.due = due
        self.message = message
        # Needs same fields as TODO

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the object to a dictionary representation.
        """
        d = self.__dict__.copy()
        for key, value in list(d.items()):
            if isinstance(value, datetime.datetime):
                d[key] = value.isoformat()
            if key.startswith("_"):
                del d[key]
            if key == "todo_meta":
                del d[key]
        return d
