"""Load and dump code tags using explicit schemas, with caller-owned streams kept open."""

from __future__ import annotations

import os
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from typing import TextIO, Union

from pycodetags.data_tags import DATA, DataTag, DataTagSchema, convert_data_tag_to_data_object, iterate_comments
from pycodetags.data_tags.formats import serialize_tag
from pycodetags.pure_data_schema import PureDataSchema
from pycodetags.schemas import PEP350Schema, TDGSchema, named_schema, resolve_schema
from pycodetags.source_io import logical_text, read_python_source

IOInput = Union[str, os.PathLike, TextIO]
IOSource = IOInput


def string_to_data(
    value: str,
    file_path: Path | None = None,
    schema: str | DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> list[DATA]:
    """Parse all tags using schema= or explicit project/path configuration."""
    selected = resolve_schema(schema, file_path)
    return [
        convert_data_tag_to_data_object(tag, selected)
        for tag in iterate_comments(value, file_path, [selected], include_folk_tags)
    ]


def string_to_data_tag_typed_dicts(
    value: str,
    file_path: Path | None = None,
    schema: str | DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> list[DataTag]:
    """Parse records without converting them to DATA instances."""
    selected = resolve_schema(schema, file_path)
    return list(iterate_comments(value, file_path, [selected], include_folk_tags))


def dumps(obj: DATA, schema: str | DataTagSchema | None = None) -> str:
    """Serialize using schema=, the record's selected schema, or explicit project configuration."""
    selected = resolve_schema(schema if schema is not None else obj.schema, obj.file_path)
    return serialize_tag(obj, selected)


def write_output(dest: IOInput, text: str) -> None:
    """Write a prepared string without closing a caller-owned stream."""
    if isinstance(dest, (str, os.PathLike)):
        Path(dest).write_text(text, encoding="utf-8")
    else:
        dest.write(text)


def dump(obj: DATA, dest: IOInput, schema: str | DataTagSchema | None = None) -> None:
    """Serialize fully before opening the destination, so invalid input cannot truncate it."""
    write_output(dest, dumps(obj, schema))


def loads(
    s: str, file_path: Path | None = None, schema: str | DataTagSchema | None = None, include_folk_tags: bool = False
) -> DATA | None:
    """Return the first tag, or None when the selected schema recognizes no tags."""
    return next(iter(string_to_data(s, file_path, schema, include_folk_tags)), None)


def read_input(source: IOInput, file_path: Path | None) -> tuple[str, Path | None]:
    """Strings are source text; Path objects are files; open streams remain caller-owned."""
    if isinstance(source, str):
        return source, file_path
    if isinstance(source, os.PathLike):
        path = Path(source)
        return path.read_text(encoding="utf-8"), file_path or path
    return source.read(), file_path


def load(
    source: IOInput,
    file_path: Path | None = None,
    schema: str | DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> DATA | None:
    """Read and parse one tag without closing an input stream supplied by the caller."""
    return next(iter(load_all(source, file_path, schema, include_folk_tags)), None)


def dumps_all(objs: Iterable[DATA], schema: str | DataTagSchema | None = None) -> str:
    """Serialize records in order, preserving their individually selected schemas."""
    return "\n".join(dumps(obj, schema) for obj in objs)


def dump_all(objs: Iterable[DATA], dest: IOInput, schema: str | DataTagSchema | None = None) -> None:
    """Prepare all records before opening the destination."""
    write_output(dest, dumps_all(objs, schema))


def load_all(
    source: IOInput,
    file_path: Path | None = None,
    schema: str | DataTagSchema | None = None,
    include_folk_tags: bool = False,
) -> list[DATA]:
    """Read and parse all tags using one explicitly selected schema."""
    if isinstance(source, os.PathLike):
        snapshot = read_python_source(source)
        tags = string_to_data(logical_text(snapshot.text), file_path or snapshot.path, schema, include_folk_tags)
        for tag in tags:
            tag.source_bytes_digest = snapshot.digest
        return tags
    text, path = read_input(source, file_path)
    return string_to_data(text, path, schema, include_folk_tags)


def loads_all(
    s: str, file_path: Path | None = None, schema: str | DataTagSchema | None = None, include_folk_tags: bool = False
) -> list[DATA]:
    """Parse all tags from source text."""
    return string_to_data(s, file_path, schema, include_folk_tags)


def inspect_file(
    file_path: str | Path, schema: str | DataTagSchema | None = None, include_folk_tags: bool = False
) -> list[DATA]:
    """Inspect a source file using its explicitly configured schema or schema=."""
    return load_all(Path(file_path), schema=schema, include_folk_tags=include_folk_tags)


def list_available_schemas() -> list[DataTagSchema]:
    """List built-ins and plugin schemas. Built-in names are reserved and cannot be overridden."""
    from pycodetags.plugin_manager import get_plugin_manager

    schemas = [TDGSchema, PEP350Schema, PureDataSchema]
    reserved = {schema["name"].casefold() for schema in schemas}
    for result in get_plugin_manager().hook.provide_schemas():
        if isinstance(result, list):
            schemas.extend(schema for schema in result if schema.get("name", "").casefold() not in reserved)
    return deepcopy(schemas)


def get_active_schemas(active_schema_names: list[str]) -> list[DataTagSchema]:
    """Resolve explicitly named schemas; unknown names are errors rather than silently ignored."""
    return [named_schema(name) for name in active_schema_names]
