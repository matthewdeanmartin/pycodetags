"""
Strongly typed data tags, base for all code tags
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field, fields
from functools import wraps
from typing import Any, Callable, cast  # noqa

try:
    from typing import Literal  # type: ignore[assignment,unused-ignore]
except ImportError:
    from typing_extensions import Literal  # type: ignore[assignment,unused-ignore] # noqa

logger = logging.getLogger(__name__)


class Serializable:
    """A base class for objects that can be serialized to a dictionary."""

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


@dataclass
class DATA(Serializable):
    """
    Represents a data record that can be serialized into python source code comments.
    """

    code_tag: str | None = "DATA"
    """Capitalized tag name"""
    comment: str | None = None
    """Unstructured text"""

    # Derived classes will have properties/fields for each data_field.
    # assignee: str

    # Custom workflow
    default_fields: dict[str, str] | None = None
    data_fields: dict[str, str] | None = None
    custom_fields: dict[str, str] | None = None
    strict: bool = False

    # Source mapping, original parsing info
    # Do not deserialize these back into the comments!
    _file_path: str | None = None
    _line_number: int | None = None
    _original_text: str | None = None
    _original_schema: str | None = None
    _offsets: tuple[int, int, int, int] | None = None

    data_meta: DATA | None = field(init=False, default=None)
    """Necessary internal field for decorators"""

    def __post_init__(self) -> None:
        """
        Validation and complex initialization
        """
        self.data_meta = self

    def _perform_action(self) -> None:
        """
        Hook for performing an action when used as a decorator or context manager.
        Override in subclasses.
        """

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Callable[..., Any]:
            self._perform_action()
            return cast(Callable[..., Any], func(*args, **kwargs))

        cast(Any, wrapper).todo_meta = self
        return wrapper

    def __enter__(self) -> DATA:
        # self._perform_action()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> Literal[False]:
        return False  # propagate exceptions

    # overridable?
    def validate(self) -> list[str]:
        """Validates the Data item."""
        return []

    def _extract_data_fields(self) -> dict[str, str]:
        d = {}
        for f in fields(self):
            # only data_fields, default_fields are strongly typed
            if f.name in ("data_fields", "default_fields"):
                continue
            val = getattr(self, f.name)
            # BUG: ignores if field is both data/default
            if val is not None:
                if isinstance(val, datetime.datetime):
                    d[f.name] = val.isoformat()
                else:
                    d[f.name] = str(val)
            else:
                print()

        return d

    def as_data_comment(self) -> str:
        """Print as if it was a PEP-350 comment."""
        the_fields = ""
        to_skip = []
        if self.default_fields:
            for key, value in self.default_fields.items():
                to_skip.append(key)
                if isinstance(value, list) and len(value) == 1:
                    value = value[0]
                elif isinstance(value, list):
                    value = ",".join(value)
                the_fields += f"{value} "

        for field_set in (self.custom_fields, self.data_fields):
            if field_set:
                for key, value in field_set.items():

                    if (
                        value  # skip blanks
                        and key != "custom_fields"
                        and key not in to_skip  # already in default
                        and not key.startswith("_")  # metadata field
                    ):
                        if isinstance(value, list) and len(value) == 1:
                            value = value[0]
                        elif isinstance(value, list):
                            value = ",".join(value)
                        else:
                            value = str(value)
                        if " " in value and "'" in value and '"' in value:
                            value = f'"""{value}"""'
                        elif " " in value and '"' not in value:
                            value = f'"{value}"'
                        elif " " in value and "'" not in value:
                            value = f"'{value}'"
                        elif ":" in value or "=" in value:
                            value = f'"{value}"'

                        the_fields += f"{key}:{value} "

        first_line = f"# {(self.code_tag or '').upper()}: {self.comment}"
        complete = f"{first_line} <{the_fields.strip()}>"
        if len(complete) > 80:
            first_line += "\n# "
            complete = f"{first_line}<{the_fields.strip()}>"
        return complete
