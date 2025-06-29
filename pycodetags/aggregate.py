"""
Aggregate live module and source files for all known schemas
"""

from __future__ import annotations

import importlib
import logging
import logging.config
import pathlib
import sys

import pycodetags.folk_code_tags as folk_code_tags
from pycodetags.collect import collect_all_data
from pycodetags.config import get_code_tags_config
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
    collected: list[DATA] = []

    for module_name in module_names:
        found = aggregate_all_kinds(module_name, "")
        collected += found

    for source_path in source_paths:
        found = aggregate_all_kinds("", source_path)
        collected += found

    return collected


def aggregate_all_kinds(module_name: str, source_path: str) -> list[DATA]:
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

    found_in_modules: list[DATA] = []
    if bool(module_name) and module_name is not None and not module_name == "None":
        logging.info(f"Checking {module_name}")
        try:
            module = importlib.import_module(module_name)
            found_in_modules = collect_all_data(module, include_submodules=False)
        except ImportError:
            print(f"Error: Could not import module(s) '{module_name}'", file=sys.stderr)

    found_tags: list[DataTag | folk_code_tags.FolkTag] = []
    schemas: list[DataTagSchema] = []
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

    found_TODOS: list[DATA] = []
    # TODO: hand off to plugin to convert to specific type
    # for found_tag in found_tags:
    #     if "fields" in found_tag.keys():
    #         found_TODOS.append(convert_pep350_tag_to_TODO(found_tag))  # type: ignore[arg-type]
    #     else:
    #         found_TODOS.append(convert_folk_tag_to_TODO(found_tag))  # type: ignore[arg-type]

    all_combined = found_TODOS + found_in_modules
    return all_combined
