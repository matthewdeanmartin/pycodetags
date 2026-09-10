"""
Collect explicitly configured source tags and live objects from Python modules.
"""

from __future__ import annotations

import importlib
import logging
import logging.config
import pathlib
from typing import Any

from pycodetags.app_config import get_code_tags_config
from pycodetags.data_tags import (
    DATA,
    DataTag,
    DataTagSchema,
    convert_data_tag_to_data_object,
    iterate_comments_from_file,
)
from pycodetags.discovery import discover_files
from pycodetags.exceptions import FileParsingError, ModuleImportError
from pycodetags.python.collect import collect_all_data

logger = logging.getLogger(__name__)


def aggregate_all_kinds_multiple_input(
    module_names: list[str],
    source_paths: list[str],
    schema: str | DataTagSchema | None = None,
    exclude: list[str] | None = None,
) -> list[DATA]:
    """Collect sources with their explicitly selected schemas, and preserve live module objects."""
    collected: list[DATA] = []
    for module_name in module_names or []:
        raw, live = aggregate_all_kinds(module_name, "", schema)
        collected.extend(live)
    visited_files: set[pathlib.Path] = set()
    for source_path in source_paths or []:
        raw, live = aggregate_all_kinds("", source_path, schema, exclude=exclude, visited_files=visited_files)
        collected.extend(convert_data_tag_to_data_object(tag, tag["schema"]) for tag in raw)
        collected.extend(live)
    return dedup_data_objects(collected)


def dedup_data_objects(tags: list[DATA]) -> list[DATA]:
    """Collect each physical source tag once across overlapping input paths.

    Live objects without source spans pass through unchanged.
    """
    seen: set[tuple[Any, ...]] = set()
    out: list[DATA] = []
    for tag in tags:
        if tag.offsets is None or tag.file_path is None:
            # No reliable source key (module-collected tag); keep it.
            out.append(tag)
            continue
        key = (str(pathlib.Path(tag.file_path).resolve()), tag.offsets, tag.code_tag, tag.comment)
        if key in seen:
            logger.debug("Deduped tag %s at %s:%s", tag.code_tag, tag.file_path, tag.offsets)
            continue
        seen.add(key)
        out.append(tag)
    return out


def aggregate_all_kinds(
    module_name: str,
    source_path: str,
    schema: str | DataTagSchema | None = None,
    exclude: list[str] | None = None,
    visited_files: set[pathlib.Path] | None = None,
) -> tuple[list[DataTag], list[DATA]]:
    """Collect one source path with per-file schema selection and optional live module objects."""
    from pycodetags.schemas import resolve_schema

    found_in_modules: list[DATA] = []
    if module_name and module_name != "None":
        try:
            module = importlib.import_module(module_name)
            found_in_modules = collect_all_data(module, include_submodules=False)
        except ImportError as error:
            raise ModuleImportError(f"Could not import module {module_name!r}") from error
    found_tags: list[DataTag] = []
    if source_path:
        path = pathlib.Path(source_path)
        config = get_code_tags_config()
        root = config.pyproject_path.parent
        if not path.resolve().is_relative_to(root):
            root = path.resolve().parent
        try:
            files = discover_files(
                root,
                [path.resolve()],
                config.config.get("exclude", []) if exclude is None else exclude,
                python_only=False,
            )
        except FileNotFoundError as error:
            raise FileParsingError(f"Cannot find Python source files in {source_path}") from error
        scanned = 0
        for file in files:
            if visited_files is not None:
                if file in visited_files:
                    scanned += 1
                    continue
                visited_files.add(file)
            if file.suffix != ".py":
                from pycodetags.plugin_manager import get_plugin_manager

                results = get_plugin_manager().hook.find_source_tags(
                    already_processed=False, file_path=str(file), config=get_code_tags_config()
                )
                plugin_tags = [tag for result in results for tag in (result or [])]
                if plugin_tags:
                    selected = resolve_schema(schema, file)
                    for tag in plugin_tags:
                        tag["schema"] = selected
                    found_tags.extend(plugin_tags)
                    scanned += 1
                continue
            selected = resolve_schema(schema, file)
            found_tags.extend(iterate_comments_from_file(str(file), schemas=[selected], include_folk_tags=False))
            scanned += 1
        if not scanned:
            raise FileParsingError(f"Cannot find Python source files in {source_path}")
    return found_tags, found_in_modules
