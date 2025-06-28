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
from pycodetags import TODO
from pycodetags.collect import collect_all_todos
from pycodetags.collection_types import CollectedTODOs
from pycodetags.config import get_code_tags_config
from pycodetags.converters import convert_folk_tag_to_TODO, convert_pep350_tag_to_TODO
from pycodetags.data_tags import DataTag
from pycodetags.data_tags_parsers import iterate_comments
from pycodetags.plugin_manager import get_plugin_manager
from pycodetags.specific_schemas import PEP350Schema

logger = logging.getLogger(__name__)


def merge_collected(all_found: list[CollectedTODOs]) -> CollectedTODOs:
    merged: CollectedTODOs = {"todos": [], "exceptions": []}
    for found in all_found:
        merged["todos"] += found.get("todos", [])
        merged["exceptions"] += found.get("exceptions", [])
    return merged


def aggregate_all_kinds_multiple_input(module_names: list[str], source_paths: list[str]) -> CollectedTODOs:
    """Refactor to support lists of modules and lists of source paths"""
    if not module_names:
        module_names = []
    if not source_paths:
        source_paths = []
    collected: CollectedTODOs = {"todos": [], "exceptions": []}

    for module_name in module_names:
        found = aggregate_all_kinds(module_name, "")
        collected["todos"] += found["todos"]
        collected["exceptions"] += found["exceptions"]
    for source_path in source_paths:
        found = aggregate_all_kinds("", source_path)
        collected["todos"] += found["todos"]
        collected["exceptions"] += found["exceptions"]
    return collected


def aggregate_all_kinds(module_name: str, source_path: str) -> CollectedTODOs:
    """
    Aggregate all TODOs and DONEs from a module and source files.

    Args:
        module_name (str): The name of the module to search in.
        source_path (str): The path to the source files.

    Returns:
        CollectedTODOs: A dictionary containing collected TODOs, DONEs, and exceptions.
    """
    config = get_code_tags_config()

    active_schemas = config.active_schemas()

    pm = get_plugin_manager()
    found_in_modules: CollectedTODOs = {}
    if bool(module_name) and module_name is not None and not module_name == "None":
        logging.info(f"Checking {module_name}")
        try:
            module = importlib.import_module(module_name)
            found_in_modules = collect_all_todos(module, include_submodules=False, include_exceptions=True)
        except ImportError:
            print(f"Error: Could not import module(s) '{module_name}'", file=sys.stderr)

    found_tags: list[DataTag | folk_code_tags.FolkTag] = []
    schemas = []
    if "todo" in active_schemas or active_schemas == []:
        schemas.append(PEP350Schema)

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

    found_TODOS: list[TODO] = []
    for found_tag in found_tags:
        if "fields" in found_tag.keys():
            found_TODOS.append(convert_pep350_tag_to_TODO(found_tag))  # type: ignore[arg-type]
        else:
            found_TODOS.append(convert_folk_tag_to_TODO(found_tag))  # type: ignore[arg-type]

    all_combined: CollectedTODOs = {
        "todos": found_TODOS + found_in_modules.get("todos", []),
        "exceptions": found_in_modules.get("exceptions", []),
    }
    return all_combined
