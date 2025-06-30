"""
Aggregate live module and source files for all known schemas
"""

from __future__ import annotations

import importlib
import logging
import logging.config
import pathlib
import sys

import pycodetags.data_schema as data_schema
import pycodetags.folk_code_tags as folk_code_tags
from pycodetags.collect import collect_all_data
from pycodetags.config import get_code_tags_config
from pycodetags.converters import convert_folk_tag_to_DATA, convert_pep350_tag_to_DATA
from pycodetags.data_schema import PureDataSchema
from pycodetags.data_tag_types import DATA
from pycodetags.data_tags import DataTag, DataTagSchema
from pycodetags.data_tags_parsers import iterate_comments
from pycodetags.plugin_manager import get_plugin_manager

logger = logging.getLogger(__name__)


def aggregate_all_kinds_multiple_input(module_names: list[str], source_paths: list[str]) -> list[DATA]:
    """Refactor to support lists of modules and lists of source paths"""
    if not module_names:
        module_names = []
    if not source_paths:
        source_paths = []
    logger.info(f"aggregate_all_kinds_multiple_input: module_names={module_names}, source_paths={source_paths}")
    collected_DATA: list[DATA] = []
    collected: list[DataTag | folk_code_tags.FolkTag] = []
    found_in_modules: list[DATA] = []
    for module_name in module_names:
        found_tags, found_in_modules = aggregate_all_kinds(module_name, "")
        collected.extend(found_tags)
        logger.debug(f"Found {len(found_in_modules)} by looking at imported module: {module_name}")

    for source_path in source_paths:
        found_tags, found_in_modules = aggregate_all_kinds("", source_path)
        collected.extend(found_tags)
        logger.debug(f"Found {len(found_tags)} by looking at src folder {source_path}")

    for found_tag in collected:
        if "fields" in found_tag.keys():
            item = convert_pep350_tag_to_DATA(found_tag, data_schema.PureDataSchema)  # type: ignore[arg-type]
            collected_DATA.append(item)
        else:
            item = convert_folk_tag_to_DATA(found_tag, data_schema.PureDataSchema)  # type: ignore[arg-type]
            collected_DATA.append(item)
    collected_DATA.extend(found_in_modules)

    return collected_DATA


def aggregate_all_kinds(
    module_name: str, source_path: str
) -> tuple[list[DataTag | folk_code_tags.FolkTag], list[DATA]]:
    """
    Aggregate all TODOs and DONEs from a module and source files.

    Args:
        module_name (str): The name of the module to search in.
        source_path (str): The path to the source files.

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
        except ImportError:
            print(f"Error: Could not import module(s) '{module_name}'", file=sys.stderr)
            raise

    found_tags: list[DataTag | folk_code_tags.FolkTag] = []
    schemas: list[DataTagSchema] = [PureDataSchema]
    # TODO: get schemas from plugins.

    if source_path:
        src_found = 0
        path = pathlib.Path(source_path)
        files = [path] if path.is_file() else path.rglob("*.*")
        for file in files:
            if file.name.endswith(".py"):
                # Finds both folk and data tags
                found_items = list(
                    _
                    for _ in iterate_comments(
                        file=str(file), schemas=schemas, include_folk_tags="folk" in active_schemas
                    )
                )
                found_tags.extend(found_items)
                src_found += 1
            else:
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
            raise TypeError(f"Can't find any files in source folder {source_path}")

    # found_TODOS: list[DATA] = []
    # TODO: hand off to plugin to convert to specific type
    # for found_tag in found_tags:
    #     if "fields" in found_tag.keys():
    #         found_TODOS.append(convert_pep350_tag_to_TODO(found_tag))  # type: ignore[arg-type]
    #     else:
    #         found_TODOS.append(convert_folk_tag_to_TODO(found_tag))  # type: ignore[arg-type]

    return found_tags, found_in_modules
