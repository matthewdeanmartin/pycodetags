"""
Support for dump, dumps, load, loads
"""

from __future__ import annotations

import io
import os
from collections.abc import Iterable
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import TextIO, Union, cast

from pycodetags.converters import convert_folk_tag_to_DATA, convert_pep350_tag_to_DATA
from pycodetags.data_schema import PureDataSchema
from pycodetags.data_tag_types import DATA
from pycodetags.data_tags import DataTag, DataTagSchema
from pycodetags.data_tags_parsers import iterate_comments
from pycodetags.folk_code_tags import FolkTag

IOInput = Union[str, os.PathLike, TextIO]
IOSource = Union[str, IOInput]


def string_to_data(
    value: str, file_path: Path | None = None, schema: DataTagSchema | None = None, include_folk_tags: bool = False
) -> Iterable[DATA]:
    """Deserialize to many code tags"""
    if schema is None:
        schema = PureDataSchema
    tags = []
    for tag in iterate_comments(value, source_file=file_path, schemas=[schema], include_folk_tags=include_folk_tags):
        if "fields" in tag:
            tags.append(convert_pep350_tag_to_DATA(cast(DataTag, tag), schema))
        else:
            tags.append(convert_folk_tag_to_DATA(cast(FolkTag, tag), schema))
    return tags


def string_to_data_tag_typed_dicts(
    value: str, file_path: Path | None = None, schema: DataTagSchema | None = None, include_folk_tags: bool = False
) -> Iterable[DataTag | FolkTag]:
    """Deserialize to many code tags"""
    if schema is None:
        schema = PureDataSchema
    tags: list[DataTag | FolkTag] = []
    for tag in iterate_comments(value, source_file=file_path, schemas=[schema], include_folk_tags=include_folk_tags):
        if "fields" in tag:
            tags.append(cast(DataTag, tag))
        else:
            tags.append(cast(FolkTag, tag))
    return tags


def _open_for_read(source: IOInput) -> StringIO | TextIOWrapper | TextIO:
    """Support for multiple ways to specify a file"""
    if isinstance(source, str):
        return io.StringIO(source)
    elif isinstance(source, os.PathLike) or isinstance(source, str):
        return open(source, encoding="utf-8")
    elif hasattr(source, "read"):
        return source  # file-like
    else:
        raise TypeError(f"Unsupported input type: {type(source)}")


def _open_for_write(dest: IOInput) -> StringIO | TextIOWrapper | TextIO:
    """Support for multiple ways to specify a file"""
    if isinstance(dest, io.StringIO):
        return dest  # already writable string buffer
    elif isinstance(dest, os.PathLike) or isinstance(dest, str):
        return open(dest, "w", encoding="utf-8")
    elif hasattr(dest, "write"):
        return dest  # file-like
    else:
        raise TypeError(f"Unsupported output type: {type(dest)}")


# mypy fails this on no-redef
# @overload
# def dump(obj: DATA, dest: str) -> None: ...
# @overload
# def dump(obj: DATA, dest: Path) -> None: ...
# @overload
# def dump(obj: DATA, dest: os.PathLike) -> None: ...
# @overload
# def dump(obj: DATA, dest: TextIO) -> None: ...

# Public API


def dumps(obj: DATA) -> str:
    """Serialize to string"""
    if not obj:
        return ""
    # TODO: check plugins to answer for _schema <matth 2025-07-04>
    return obj.as_data_comment()


def dump(obj: DATA, dest: Union[str, Path, os.PathLike, TextIO]) -> None:
    """Serialize to a file-like or path-like"""
    with _open_for_write(dest) as f:
        f.write(obj.as_data_comment())


def loads(
    s: str, file_path: Path | None = None, schema: DataTagSchema | None = None, include_folk_tags: bool = False
) -> DATA | None:
    """Deserialize from a string to a single data tag"""
    items = string_to_data(s, file_path, schema, include_folk_tags)
    return next((_ for _ in items), None)


def load(
    source: IOInput, file_path: Path | None = None, schema: DataTagSchema | None = None, include_folk_tags: bool = False
) -> DATA | None:
    """Deserialize from a file-like or path-like to a single data tag"""
    # BUG: not all of these are context manager <matth 2025-07-05>
    with _open_for_read(source) as f:
        items = string_to_data(f.read(), file_path, schema, include_folk_tags)
        return next((_ for _ in items), None)


def dump_all(objs: Iterable[DATA], dest: IOInput) -> None:
    """Deserialize many data tags to a file-like or path-like"""
    with _open_for_write(dest) as f:
        for obj in objs:
            f.write(obj.as_data_comment() + "\n")


def dumps_all(objs: Iterable[DATA]) -> str:
    """Serialize many data tags to a string"""
    return "\n".join(obj.as_data_comment() for obj in objs)


def load_all(
    source: IOInput, file_path: Path | None = None, schema: DataTagSchema | None = None, include_folk_tags: bool = False
) -> Iterable[DATA]:
    """Deserialize many data tags from a file-like or path-like"""
    with _open_for_read(source) as f:
        return string_to_data(f.read(), file_path, schema, include_folk_tags)


def loads_all(
    s: str, file_path: Path | None = None, schema: DataTagSchema | None = None, include_folk_tags: bool = False
) -> Iterable[DATA]:
    """Deserialize many data tags from a string"""
    return string_to_data(s, file_path, schema, include_folk_tags)
