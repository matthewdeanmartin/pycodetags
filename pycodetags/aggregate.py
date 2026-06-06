"""
Searches for tags three different ways: Data Tags and Folk Tags in source code. Also searches for live objects
in the object graph of the specified modules.
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
from pycodetags.exceptions import FileParsingError, ModuleImportError
from pycodetags.pure_data_schema import PureDataSchema
from pycodetags.python.collect import collect_all_data

logger = logging.getLogger(__name__)


def aggregate_all_kinds_multiple_input(
    module_names: list[str], source_paths: list[str], schema: DataTagSchema
) -> list[DATA]:
    """Refactor to support lists of modules and lists of source paths

    Args:
        module_names (list[str]): List of module names to search in.
        source_paths (list[str]): List of source paths to search in.
        schema (DataTagSchema): The schema to use for the data tags.

    Returns:
        list[DATA]: A list of DATA objects containing collected TODOs and DATA.
    """
    if not module_names:
        module_names = []
    if not source_paths:
        source_paths = []
    if schema is None:
        schema = PureDataSchema
    logger.info(f"aggregate_all_kinds_multiple_input: module_names={module_names}, source_paths={source_paths}")
    collected_DATA: list[DATA] = []
    collected: list[DataTag] = []
    found_in_modules: list[DATA] = []

    # AST Tags
    for module_name in module_names:
        found_tags, found_in_modules = aggregate_all_kinds(module_name, "", schema)
        collected.extend(found_tags)
        logger.debug(f"Found {len(found_in_modules)} by looking at imported module: {module_name}")

    # Source Tags
    for source_path in source_paths:
        found_tags, found_in_modules = aggregate_all_kinds("", source_path, schema)
        collected.extend(found_tags)
        logger.debug(f"Found {len(found_tags)} by looking at src folder {source_path}")

    for found_tag in collected:
        item = convert_data_tag_to_data_object(found_tag, schema)
        collected_DATA.append(item)
    collected_DATA.extend(found_in_modules)

    return dedup_data_objects(collected_DATA)


def dedup_data_objects(tags: list[DATA]) -> list[DATA]:
    """Drop duplicate tags produced when several active schemas match the same comment block.

    When both ``PureDataSchema`` and a plugin schema (e.g. the issue-tracker ``TODO`` schema) recognize
    the same ``# TODO:`` block, the same physical tag is collected once per schema. They share a file
    path, offsets, tag name, and comment, so we key on that tuple and keep the first occurrence.

    Tags without source mapping (e.g. live objects collected from modules, which have no offsets) are
    never deduped against each other -- their identity tuple is unique enough only by object, so they
    pass through untouched.

    Args:
        tags: Collected DATA objects, in discovery order.

    Returns:
        The list with block-level duplicates removed, order preserved.
    """
    seen: set[tuple[Any, ...]] = set()
    out: list[DATA] = []
    for tag in tags:
        if tag.offsets is None or tag.file_path is None:
            # No reliable source key (module-collected tag); keep it.
            out.append(tag)
            continue
        key = (tag.file_path, tag.offsets, tag.code_tag, tag.comment)
        if key in seen:
            logger.debug("Deduped tag %s at %s:%s", tag.code_tag, tag.file_path, tag.offsets)
            continue
        seen.add(key)
        out.append(tag)
    return out


def aggregate_all_kinds(module_name: str, source_path: str, schema: DataTagSchema) -> tuple[list[DataTag], list[DATA]]:
    """
    Aggregate all TODOs and DONEs from a module and source files.

    Args:
        module_name (str): The name of the module to search in.
        source_path (str): The path to the source files.
        schema (DataTagSchema): The schema to use for the data tags.

    Returns:
        list[DATA]: A dictionary containing collected TODOs, DONEs, and exceptions.
    """
    config = get_code_tags_config()

    active_schemas = config.active_schemas()

    logger.info(
        f"aggregate_all_kinds: module_name={module_name}, source_path={source_path}, active_schemas={active_schemas}"
    )
    found_in_modules: list[DATA] = []
    if bool(module_name) and module_name is not None and not module_name == "None":
        logging.info(f"Checking {module_name}")
        try:
            module = importlib.import_module(module_name)
            found_in_modules = collect_all_data(module, include_submodules=False)
        except ImportError as ie:
            logger.error(f"Error: Could not import module(s) '{module_name}'")
            raise ModuleImportError(f"Error: Could not import module(s) '{module_name}'") from ie

    found_tags: list[DataTag] = []
    schemas: list[DataTagSchema] = [schema]
    # Add plugin-provided schemas the user activated (e.g. "TDG"), so TDG-format comments are parsed
    # alongside the primary schema. PureDataSchema / the passed schema are not duplicated.
    from pycodetags.common_interfaces import get_active_schemas

    for extra in get_active_schemas(active_schemas):
        if extra.get("name") != schema.get("name"):
            schemas.append(extra)

    if source_path:
        src_found = 0
        path = pathlib.Path(source_path)
        files = [path] if path.is_file() else path.rglob("*.*")
        for file in files:
            if file.name.endswith(".py"):
                # Finds both folk and data tags
                found_items = list(
                    _
                    for _ in iterate_comments_from_file(
                        str(file), schemas=schemas, include_folk_tags="folk" in active_schemas
                    )
                )
                found_tags.extend(found_items)
                src_found += 1
            else:
                from pycodetags.plugin_manager import get_plugin_manager

                pm = get_plugin_manager()
                # Collect folk tags from plugins
                plugin_results = pm.hook.find_source_tags(
                    already_processed=False, file_path=str(file), config=get_code_tags_config()
                )
                for result_list in plugin_results:
                    found_tags.extend(result_list)
                if plugin_results:
                    src_found += 1
        if src_found == 0:
            raise FileParsingError(f"Can't find any files in source folder {source_path}")

    return found_tags, found_in_modules
