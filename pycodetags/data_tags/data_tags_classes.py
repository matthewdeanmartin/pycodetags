"""
Strongly typed data tags, base for all code tags
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field, fields
from functools import wraps
from typing import Any, Callable, cast  # noqa

from pycodetags.exceptions import DataTagError, ValidationError

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
            if key == "data_meta":
                del d[key]
        return d


@dataclass(eq=False)
class DATA(Serializable):
    """
    Represents a data record that can be serialized into python source code comments.
    """

    code_tag: str | None = "DATA"
    """Capitalized tag name"""
    comment: str | None = None
    """Unstructured text"""

    # Shared narrative fields for both explicitly selected formats.
    title: str | None = None
    """First-line title. Parsed comment mirrors this value; edit title to change it."""
    body: str | None = None
    """Body text, with internal blank lines preserved; empty string for title-only tags."""

    # Local identity. NOT auto-assigned during parsing; filled by a tool. The comment field name is
    # ``id`` (e.g. ``id=42``); the attribute is ``tag_id`` to avoid shadowing the ``id`` builtin.
    tag_id: str | None = None
    """Local identity (``id=N`` in source). Tool-assigned, stable once set."""

    # Derived classes will have properties/fields for each data_field.
    # assignee: str

    # Custom as per domain specific schema
    default_fields: dict[str, str] | None = None
    data_fields: dict[str, str] | None = None
    custom_fields: dict[str, str] | None = None
    identity_fields: list[str] | None = None
    unprocessed_defaults: list[str] | None = None

    # Source mapping, original parsing info
    # Do not deserialize these back into the comments!
    file_path: str | None = None
    source_digest: str | None = None
    """Logical source snapshot fingerprint for stale-write detection."""
    source_bytes_digest: str | None = None
    """Exact file fingerprint when loaded directly from disk."""
    original_text: str | None = None
    original_schema: str | None = None
    schema: dict[str, Any] | None = None
    """Explicit schema captured during parsing, used when writing this record."""
    offsets: tuple[int, int, int, int] | None = None

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

        cast(Any, wrapper).data_meta = self
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

    def validate_or_raise(self) -> None:
        errors = self.validate()
        if errors:
            raise ValidationError(errors)

    def _extract_data_fields(self) -> dict[str, str]:
        d = {}
        for f in fields(self):
            # only data_fields, default_fields are strongly typed
            if f.name in ("data_fields", "default_fields"):
                continue
            val = getattr(self, f.name)
            # BUG: ignores if field is both data/default <matth 2025-07-04
            #  category:core priority:high status:development release:1.0.0 iteration:1>
            if val is not None:
                if isinstance(val, datetime.datetime):
                    d[f.name] = val.isoformat()
                else:
                    d[f.name] = str(val)
            # else:
            #     print()

        return d

    def as_data_comment(self, schema=None) -> str:
        """Serialize using an explicit schema, recorded parse schema, or project configuration."""
        from pycodetags.common_interfaces import dumps

        return dumps(self, schema=schema)

    def __eq__(self, other: object) -> bool:
        # @dataclasses autogenerated __eq__ calls __repr__ so eval(repr(x)) == x causes infinite loop detection

        # TODO: this needs to support subclasses. <matth 2025-07-04
        #  category:core priority:high status:development release:1.0.0 iteration:1>

        # if not isinstance(other, type(self)):
        #     return NotImplemented

        for f in fields(self):
            self_val = getattr(self, f.name)
            other_val = getattr(other, f.name)

            # Skip self-references (simple identity check)
            if self_val is self and other_val is other:
                continue

            if self_val != other_val:
                return False

        return True

    def __repr__(self) -> str:
        field_strings = []
        for f in fields(self):
            if f.name not in ("data_meta", "type"):
                field_strings.append(f"{f.name}={getattr(self, f.name)!r}")
        return f"{self.__class__.__name__}({', '.join(field_strings)})"

    def content_identity(self, schema: Any) -> str:
        """Stable short hash of this tag's identity fields. See ``data_tags.identity``."""
        # Imported lazily to avoid a cycle (identity imports the schema module, not this one).
        from pycodetags.data_tags.identity import content_identity_for_data

        return content_identity_for_data(self, schema)

    def terminal_link(self) -> str:
        """In JetBrains IDE Terminal, will hyperlink to file"""
        if self.offsets:
            start_line, start_char, _end_line, _end_char = self.offsets
            return f"{self.file_path}:{start_line+1}:{start_char}"
        if self.file_path:
            return f"{self.file_path}:0"
        return ""

    def to_flat_dict(self, include_comment_and_tag: bool = False, raise_on_doubles: bool = True) -> dict[str, Any]:

        # TODO: see if there is way to disambiguate to_flat_dict and to_dict (in the serializer) <matth 2025-07-05
        #   category:documentation priority:low status:development release:1.0.0 iteration:1>
        if self.data_fields:
            data = self.data_fields.copy()
        else:
            data = {}
        if self.custom_fields:
            for key, value in self.custom_fields.items():
                if raise_on_doubles and key in data:
                    raise DataTagError("Field in data_fields and custom fields")
                data[key] = value
        if self.tag_id is not None:
            data["id"] = self.tag_id
        if self.title is not None:
            data["title"] = self.title
        if self.body is not None:
            data["body"] = self.body
        if include_comment_and_tag:
            if self.comment:
                data["comment"] = self.comment
            if self.code_tag:
                data["code_tag"] = self.code_tag
        return data
