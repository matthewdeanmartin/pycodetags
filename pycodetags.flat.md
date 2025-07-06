# Contents of pycodetags source tree

## File: aggregate.py

```python
"""
Aggregate live module and source files for all known schemas
"""

from __future__ import annotations

import importlib
import logging
import logging.config
import pathlib

import pycodetags.data_tags_schema as data_schema
import pycodetags.folk_code_tags as folk_code_tags
from pycodetags.collect import collect_all_data
from pycodetags.config import get_code_tags_config
from pycodetags.converters import convert_data_tag_to_data_object, convert_folk_tag_to_DATA
from pycodetags.data_tags_classes import DATA
from pycodetags.data_tags_parsers import iterate_comments_from_file
from pycodetags.data_tags_schema import DataTag, DataTagSchema
from pycodetags.exceptions import FileParsingError, ModuleImportError
from pycodetags.plugin_manager import get_plugin_manager

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
        schema = data_schema.PureDataSchema
    logger.info(f"aggregate_all_kinds_multiple_input: module_names={module_names}, source_paths={source_paths}")
    collected_DATA: list[DATA] = []
    collected: list[DataTag | folk_code_tags.FolkTag] = []
    found_in_modules: list[DATA] = []
    for module_name in module_names:
        found_tags, found_in_modules = aggregate_all_kinds(module_name, "", schema)
        collected.extend(found_tags)
        logger.debug(f"Found {len(found_in_modules)} by looking at imported module: {module_name}")

    for source_path in source_paths:
        found_tags, found_in_modules = aggregate_all_kinds("", source_path, schema)
        collected.extend(found_tags)
        logger.debug(f"Found {len(found_tags)} by looking at src folder {source_path}")

    for found_tag in collected:
        if "fields" in found_tag.keys():
            item = convert_data_tag_to_data_object(found_tag, schema)  # type: ignore[arg-type]
            collected_DATA.append(item)
        else:
            item = convert_folk_tag_to_DATA(found_tag, schema)  # type: ignore[arg-type]
            collected_DATA.append(item)
    collected_DATA.extend(found_in_modules)

    return collected_DATA


def aggregate_all_kinds(
    module_name: str, source_path: str, schema: DataTagSchema
) -> tuple[list[DataTag | folk_code_tags.FolkTag], list[DATA]]:
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

    found_tags: list[DataTag | folk_code_tags.FolkTag] = []
    schemas: list[DataTagSchema] = [schema]
    # TODO: get schemas from plugins.<matth 2025-07-04
    #   category:plugin priority:medium status:development release:1.0.0 iteration:1>

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

```

## File: collect.py

```python
"""
Finds all strongly typed code tags in a module.

Three ways to find strongly typed TODOs:

- import module, walk the object graph. Easy to miss anything without a public interface
- See other modules for techniques using AST parsing
- See other modules for source parsing.

"""

from __future__ import annotations

import inspect
import logging
import os
import sysconfig
import types
from types import ModuleType, SimpleNamespace
from typing import Any

from pycodetags import DATA

logger = logging.getLogger(__name__)


def is_stdlib_module(module: types.ModuleType | SimpleNamespace) -> bool:
    """
    Check if a module is part of the Python standard library.

    Args:
        module: The module to check

    Returns:
        bool: True if the module is part of the standard library, False otherwise
    """
    # Built-in module (no __file__ attribute, e.g. 'sys', 'math', etc.)
    if not hasattr(module, "__file__"):
        return True

    stdlib_path = sysconfig.get_paths()["stdlib"]
    the_path = getattr(module, "__file__", "")
    if not the_path:
        return True
    module_path = os.path.abspath(the_path)

    return module_path.startswith(os.path.abspath(stdlib_path))


class DATACollector:
    """Comprehensive collector for DATA items."""

    def __init__(self) -> None:
        self.data: list[DATA] = []
        self.visited: set[int] = set()

    def collect_from_module(
        self, module: ModuleType, include_submodules: bool = True, max_depth: int = 10
    ) -> list[DATA]:
        """
        Collect all DATA items.

        Args:
            module: The module to inspect
            include_submodules: Whether to recursively inspect submodules
            max_depth: Maximum recursion depth for submodules

        Returns:
            list of DATA
        """
        logger.info(f"Collecting from module {module.__name__} with max depth {max_depth}")
        self._reset()
        self._collect_recursive(module, include_submodules, max_depth, 0)
        return self.data.copy()

    def _reset(self) -> None:
        """Reset internal collections."""
        self.data.clear()
        self.visited.clear()

    def _collect_recursive(self, obj: Any, include_submodules: bool, max_depth: int, current_depth: int) -> None:
        """Recursively collect TODO/Done items from an object.

        Args:
            obj: The object to inspect
            include_submodules: Whether to recursively inspect submodules
            max_depth: Maximum recursion depth for submodules
            current_depth: Current recursion depth
        """
        if current_depth > max_depth or id(obj) in self.visited:
            if current_depth > max_depth:
                logger.debug(f"Maximum depth {max_depth}")
            else:
                logger.debug(f"Already visited {id(obj)}")
            return

        self.visited.add(id(obj))

        # Check if object itself is a TODO/Done item
        # self._check_object_for_todos(obj)

        # Handle modules
        if inspect.ismodule(obj) and not is_stdlib_module(obj):
            logger.debug(f"Collecting module {obj}")
            self._collect_from_module_attributes(obj, include_submodules, max_depth, current_depth)

        if isinstance(obj, SimpleNamespace):
            logger.debug(f"Collecting namespace {obj}")
            self._collect_from_module_attributes(obj, include_submodules, max_depth, current_depth)

        # Handle classes
        if inspect.isclass(obj):
            logger.debug(f"Collecting class {obj}")
            self._collect_from_class_attributes(obj, include_submodules, max_depth, current_depth)

        # Handle functions and methods
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            logger.debug(f"Collecting function/method {obj}")
            self._check_object_for_metadata(obj)
            # Classes are showing up as functions?! Yes.
            self._collect_from_class_attributes(obj, include_submodules, max_depth, current_depth)
        if isinstance(obj, (list, set, tuple)) and obj:
            logger.debug(f"Found a list/set/tuple {obj}")
            for item in obj:
                self._check_object_for_metadata(item)
        else:
            # self._collect_from_class_attributes(obj, include_submodules, max_depth, current_depth)
            logger.debug(f"Don't know what to do with {obj}")

    def _check_object_for_metadata(self, obj: Any) -> None:
        """Check if an object has metadata."""
        if hasattr(obj, "data_meta"):
            if isinstance(obj.data_meta, DATA):
                logger.info(f"Found todo, by instance and has data_meta attr on {obj}")
                self.data.append(obj.data_meta)

    def _collect_from_module_attributes(
        self, module: ModuleType | SimpleNamespace, include_submodules: bool, max_depth: int, current_depth: int
    ) -> None:
        """Collect from all attributes of a module.

        Args:
            module: The module to inspect
            include_submodules: Whether to recursively inspect submodules
            max_depth: Maximum recursion depth for submodules
            current_depth: Current recursion depth
        """
        if is_stdlib_module(module) or module.__name__ == "builtins":
            return

        for attr_name in dir(module):
            if attr_name.startswith("__"):
                continue
            # User could put a TODO on a private method and even if it isn't exported, it still is a TODO
            # if attr_name.startswith("_"):
            #     continue

            logger.debug(f"looping : {module} : {attr_name}")

            try:
                attr = getattr(module, attr_name)

                # Handle submodules
                if include_submodules and inspect.ismodule(attr):
                    # Avoid circular imports and built-in modules
                    if (
                        hasattr(attr, "__file__")
                        and attr.__file__ is not None
                        and not attr.__name__.startswith("builtins")
                    ):
                        self._collect_recursive(attr, include_submodules, max_depth, current_depth + 1)
                # elif isinstance(list, attr) and attr:
                #     for item in attr:
                #         self._collect_recursive(item, include_submodules, max_depth, current_depth + 1)
                # elif is_stdlib_module(module) or module.__name__ == "builtins":
                #     pass
                else:
                    logger.debug(f"Collecting something ...{attr_name}: {attr}")
                    self._collect_recursive(attr, include_submodules, max_depth, current_depth + 1)

            except (AttributeError, ImportError, TypeError):
                # Skip attributes that can't be accessed
                continue

    def _collect_from_class_attributes(
        self,
        cls: type | types.FunctionType | types.MethodType,
        include_submodules: bool,
        max_depth: int,
        current_depth: int,
    ) -> None:
        """
        Collect from all attributes of a class.

        Args:
            cls: The class to inspect
            include_submodules: Whether to recursively inspect submodules
            max_depth: Maximum recursion depth for submodules
            current_depth: Current recursion depth
        """
        logger.debug("Collecting from class attributes ------------")
        # Check class methods and attributes
        for attr_name in dir(cls):
            if attr_name.startswith("__"):
                continue

            try:
                attr = getattr(cls, attr_name)
                self._collect_recursive(attr, include_submodules, max_depth, current_depth + 1)
            except (AttributeError, TypeError):
                logger.error(f"ERROR ON attr_name {attr_name}")
                continue

    def collect_standalone_items(self, items_list: list[DATA]) -> list[DATA]:
        """
        Collect standalone DATA items from a list.

        Args:
            items_list: List containing DATA instances

        Returns:
            list of DATA
        """
        data = [item for item in items_list if isinstance(item, DATA)]
        return data


def collect_all_data(
    module: ModuleType,
    standalone_items: list[DATA] | None = None,
    include_submodules: bool = True,
) -> list[DATA]:
    """
    Comprehensive collection of all DATA items and exceptions.

    Args:
        module: Module to inspect
        standalone_items: List of standalone TODO/Done items
        include_submodules: Whether to inspect submodules

    Returns:
        Dictionary with 'todos', 'dones', and 'exceptions' keys
    """
    collector = DATACollector()

    todos = collector.collect_from_module(module, include_submodules)
    logger.info(f"Found {len(todos)} DATA in module '{module.__name__}'.")

    # Collect standalone items if provided
    if standalone_items:
        standalone_todos = collector.collect_standalone_items(standalone_items)
        logger.info(f"Found {len(standalone_todos)} standalone DATA.")
        todos.extend(standalone_todos)

    return todos

```

## File: comment_finder.py

```python
"""
Finds comments using the AST parser.

If we look for comments with regex, we risk finding comments inside of structure that are not comments.

For older versions of python, the code falls back to string parsing instead of AST parsing.

Once a comment block is found, it could still have multiple code tags in it.
"""

from __future__ import annotations

import logging
from ast import walk
from typing import Any

from pycodetags.exceptions import FileParsingError
from pycodetags.utils import persistent_memoize

try:
    from ast_comments import Comment, parse
except ImportError:
    Comment: Any = None  # type: ignore[no-redef]
    parse: Any = None  # type: ignore[no-redef]

LOGGER = logging.getLogger(__name__)

__all__ = ["find_comment_blocks_from_string", "find_comment_blocks_from_string_fallback"]


@persistent_memoize(ttl_seconds=60 * 60 * 24 * 7, use_gzip=True)
def find_comment_blocks_from_string(source: str) -> list[tuple[int, int, int, int, str]]:
    """Parses a Python source file and yields comment block ranges.

    Uses `ast-comments` to locate all comments, and determines the exact offsets
    for each block of contiguous comments.

    Args:
        source (str): Python source text.

    Returns:
        list[tuple[int, int, int, int, str]]: (start_line, start_char, end_line, end_char, comment)
        representing the comment block's position in the file (0-based).
    """
    blocks: list[tuple[int, int, int, int, str]] = []
    if parse is None:
        # Hack for 3.7!
        return find_comment_blocks_from_string_fallback(source)
        # type: ignore[no-redef,unused-ignore]

    if not source:
        return blocks

    tree = parse(source)
    lines = source.splitlines()

    # Filter out comment nodes
    # BUG: fails to walk the whole tree. This is shallow. <matth 2025-07-04
    #  category:parser priority:high status:development release:1.0.0 iteration:1>
    comments = [node for node in walk(tree) if isinstance(node, Comment)]

    def comment_pos(comment: Comment) -> tuple[int, int, int, int]:
        """Get the position of a comment as (start_line, start_char, end_line, end_char)."""
        for i, line in enumerate(lines):
            idx = line.find(comment.value)
            if idx != -1:
                return (i, idx, i, idx + len(comment.value))
        raise FileParsingError(f"Could not locate comment in source: {comment.value}")

    # Group comments into blocks
    block: list[tuple[int, int, int, int]] = []

    for comment in comments:
        pos = comment_pos(comment)

        if not block:
            block.append(pos)
        else:
            prev_end_line = block[-1][2]
            if pos[0] == prev_end_line + 1:
                # Consecutive line: extend block
                block.append(pos)
            else:
                # Yield previous block
                start_line, start_char, _, _ = block[0]
                end_line, _, _, end_char = block[-1]
                final_comment = extract_comment_text(source, (start_line, start_char, end_line, end_char))
                blocks.append((start_line, start_char, end_line, end_char, final_comment))
                block = [pos]

    if block:
        start_line, start_char, _, _ = block[0]
        end_line, _, _, end_char = block[-1]
        final_comment = extract_comment_text(source, (start_line, start_char, end_line, end_char))
        blocks.append((start_line, start_char, end_line, end_char, final_comment))
    return blocks


def extract_comment_text(text: str, offsets: tuple[int, int, int, int]) -> str:
    """Extract the comment text from a file given start/end line/char offsets.

    Args:
        text (str): text of source code
        offsets (tuple): A tuple of (start_line, start_char, end_line, end_char),
            all 0-based.

    Returns:
        str: The exact substring from the file containing the comment block.
    """
    start_line, start_char, end_line, end_char = offsets

    lines = text.splitlines()

    if start_line == end_line:
        return lines[start_line][start_char:end_char]

    # Multi-line block
    block_lines = [lines[start_line][start_char:]]
    for line_num in range(start_line + 1, end_line):
        block_lines.append(lines[line_num])
    block_lines.append(lines[end_line][:end_char])

    return "\n".join(block_lines)


def find_comment_blocks_from_string_fallback(source: str) -> list[tuple[int, int, int, int, str]]:
    """Parse Python source and yield comment block positions and content.

    Args:
        source (str): Python source file.

    Returns:
        list[tuple[int, int, int, int, str]]: A tuple of (start_line, start_char, end_line, end_char, comment)
        representing the block's location and the combined comment text. All indices are 0-based.
    """
    blocks = []

    lines = source.split("\n")

    in_block = False
    start_line = start_char = 0
    end_line = end_char = 0
    comment_lines: list[str] = []

    for idx, line in enumerate(lines):
        line_wo_newline = line.rstrip("\n")
        comment_pos = line.find("#")

        if comment_pos != -1:
            if not in_block:
                # Start a new block
                in_block = True
                start_line = idx
                start_char = comment_pos
                comment_lines = []
                LOGGER.debug("Starting comment block at line %d, char %d", start_line, start_char)

            end_line = idx
            end_char = len(line_wo_newline)
            comment_lines.append(line_wo_newline[comment_pos:])

            # Check if next line is non-comment or this is a standalone inline comment
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            next_comment_pos = next_line.find("#")
            next_stripped = next_line.strip()

            if not next_stripped or next_comment_pos == -1:
                # End of comment block
                comment_text = "\n".join(comment_lines)
                LOGGER.debug("Ending comment block at line %d, char %d", end_line, end_char)
                blocks.append((start_line, start_char, end_line, end_char, comment_text))
                in_block = False

        else:
            if in_block:
                # Previous line had comment, current one doesn't: close block
                comment_text = "\n".join(comment_lines)
                LOGGER.debug("Ending comment block at line %d, char %d", end_line, end_char)
                blocks.append((start_line, start_char, end_line, end_char, comment_text))
                in_block = False

    if in_block:
        comment_text = "\n".join(comment_lines)
        LOGGER.debug("Ending final comment block at line %d, char %d", end_line, end_char)
        blocks.append((start_line, start_char, end_line, end_char, comment_text))
    return blocks


if parse is None:
    # Hack for 3.7!
    find_comment_blocks_from_string = find_comment_blocks_from_string_fallback  # type: ignore[no-redef,unused-ignore]

```

## File: common_interfaces.py

```python
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

from pycodetags.converters import convert_data_tag_to_data_object, convert_folk_tag_to_DATA
from pycodetags.data_tags_classes import DATA
from pycodetags.data_tags_parsers import iterate_comments
from pycodetags.data_tags_schema import DataTag, DataTagSchema
from pycodetags.folk_code_tags import FolkTag
from pycodetags.pure_data_schema import PureDataSchema

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
            tags.append(convert_data_tag_to_data_object(cast(DataTag, tag), schema))
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
    # TODO: check plugins to answer for _schema <matth 2025-07-04
    #  category:plugin priority:medium status:development release:1.0.0 iteration:1>
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
    # BUG: not all of these are context manager <matth 2025-07-05
    #  category:core priority:high status:development release:1.0.0 iteration:1>
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

```

## File: config.py

```python
"""
Config for pycodetags library.

This is a basically valid config
```toml
[tool.pycodetags]
# Range Validation, Range Sources

# Empty list means use file
# If validated, originator and assignee must be on author list
valid_authors = []
valid_authors_file = "AUTHORS.md"
# Can be Gnits, single_column, humans.txt
valid_authors_schema = "single_column"

# Active can be validated against author list.
# Active user from "os", "env", "git"
user_identification_technique = "os"
# .env variable if method is "env"
user_env_var = "PYCODETAGS_USER"

# Case insensitive. Needs at least "done"
valid_status = [
    "planning",
    "ready",
    "done",
    "development",
    "inprogress",
    "testing",
    "closed",
    "fixed",
    "nobug",
    "wontfix"
]

# Categories, priorities, iterations are only displayed
valid_categories = []
valid_priorities = ["high", "medium", "low"]

# Used to support change log generation and other features.
closed_status = ["done", "closed", "fixed", "nobug", "wontfix"]

# Empty list means no restrictions
valid_releases = []

# Use to look up valid releases (versions numbers)
valid_releases_file = "CHANGELOG.md"
valid_releases_file_schema = "CHANGELOG.md"

# Used in sorting and views
releases_schema = "semantic"

# Subsection of release. Only displayed.
valid_iterations = ["1", "2", "3", "4"]

# Empty list means all are allowed
valid_custom_field_names = []

# Originator and origination date are important for issue identification
# Without it, heuristics are more likely to fail to match issues to their counterpart in git history
mandatory_fields = ["originator", "origination_date"]

# Helpful for parsing tracker field, used to make ticket a clickable url
tracker_domain = "example.com"
# Can be url or ticket
tracker_style = "url"

# Defines the action for a TODO condition: "stop", "warn", "nothing".
enable_actions = true
default_action = "warn"
action_on_past_due = true
action_only_on_responsible_user = true

# Environment detection
disable_on_ci = true

# Use .env file
use_dot_env = true
```

"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from pycodetags.exceptions import ConfigError

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import toml
    except ImportError:
        # This probably shouldn't raise in a possible production environment.
        pass


logger = logging.getLogger(__name__)


def careful_to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("false", "0"):
        return False
    if value is None:
        return default
    if value == "":
        return default
    return default


class CodeTagsConfig:
    _instance: CodeTagsConfig | None = None
    config: dict[str, Any] = {}

    def __init__(self, pyproject_path: str = "pyproject.toml"):

        self._pyproject_path = pyproject_path
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._pyproject_path):
            self.config = {}
            return

        with open(self._pyproject_path, "rb" if "tomllib" in sys.modules else "r") as f:
            # pylint: disable=used-before-assignment
            data = tomllib.load(f) if "tomllib" in sys.modules else toml.load(f)

        self.config = data.get("tool", {}).get("pycodetags", {})

    def disable_all_runtime_behavior(self) -> bool:
        """Minimize performance costs when in production"""
        return careful_to_bool(self.config.get("disable_all_runtime_behavior", False), False)

    def enable_actions(self) -> bool:
        """Enable logging, warning, and stopping (TypeError raising)"""
        return careful_to_bool(self.config.get("enable_actions", False), False)

    def default_action(self) -> str:
        """Do actions log, warn, stop or do nothing"""
        field = "default_action"
        result = self.config.get(field, "")
        accepted = ("warn", "warning", "stop", "nothing", "")
        if result not in accepted:
            raise ConfigError(f"Invalid configuration: {field} must be in {accepted}")
        return str(result)

    def disable_on_ci(self) -> bool:
        """Disable actions on CI, overrides other."""
        return careful_to_bool(self.config.get("disable_on_ci", True), True)

    def use_dot_env(self) -> bool:
        """Look for a load .env"""
        return careful_to_bool(self.config.get("use_dot_env", True), True)

    @property
    def runtime_behavior_enabled(self) -> bool:
        """Check if runtime behavior is enabled based on the config."""
        return bool(self.config) and not careful_to_bool(self.config.get("disable_all_runtime_behavior", False), False)

    def modules_to_scan(self) -> list[str]:
        """Allows user to skip listing modules on CLI tool"""
        return [_.lower() for _ in self.config.get("modules", [])]

    def source_folders_to_scan(self) -> list[str]:
        """Allows user to skip listing src on CLI tool"""
        return [_.lower() for _ in self.config.get("src", [])]

    def active_schemas(self) -> list[str]:
        """Schemas to detect in source comments."""
        return [str(_).lower() for _ in self.config.get("active_schemas", [])]

    @classmethod
    def get_instance(cls, pyproject_path: str = "pyproject.toml") -> CodeTagsConfig:
        """Get the singleton instance of CodeTagsConfig."""
        if cls._instance is None:
            cls._instance = cls(pyproject_path)
        return cls._instance

    @classmethod
    def set_instance(cls, instance: CodeTagsConfig | None) -> None:
        """Set a custom instance of CodeTagsConfig."""
        cls._instance = instance


def get_code_tags_config() -> CodeTagsConfig:
    return CodeTagsConfig.get_instance()

```

## File: config_init.py

```python
from __future__ import annotations

import os


def init_pycodetags_config():
    """
    Initializes the [tool.pycodetags] section in pyproject.toml with 0 dependencies.

    This interactive script will:
    1. Check for an existing `pycodetags` configuration and exit if found.
    2. Scan the current directory for potential Python source folders.
    3. Ask the user to confirm the correct source folder.
    4. Generate a default configuration for pycodetags with helpful comments.
    5. Safely add this configuration to `pyproject.toml`, creating the file if it
       doesn't exist.
    """
    pyproject_path = "pyproject.toml"
    print("--- PyCodeTags Config Initializer ---")

    # Step 1: Check if the configuration already exists to prevent overwriting.
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, encoding="utf-8") as f:
                content = f.read()
            if "[tool.pycodetags]" in content:
                print(f"\nConfiguration for '[tool.pycodetags]' already exists in {pyproject_path}.")
                print("Initialization is not needed. Please edit the file manually for any changes.")
                return
        except OSError as e:
            print(f"Error reading {pyproject_path}: {e}")
            return

    # Step 2: Find potential source folders and get user selection.
    print("\nSearching for potential source code folders...")
    potential_folders = _find_potential_src_folders()

    if not potential_folders:
        print("Could not automatically detect any source folders.")
        src_folder = input("Please manually enter the path to your source folder (e.g., 'src', 'my_app'): ")
    else:
        src_folder = _select_src_folder_interactive(potential_folders) or ""

    if not src_folder or not src_folder.strip():
        print("\nNo source folder selected. Aborting initialization.")
        return

    print(f"\nUsing '{src_folder}' as the primary source folder.")

    # Step 3: Generate the TOML content.
    toml_section = _generate_pycodetags_toml_section(src_folder)

    # Step 4: Safely write the content to pyproject.toml.
    _write_to_pyproject_safe(toml_section, pyproject_path)

    print("\nInitialization complete! You can now customize the settings in pyproject.toml.")


def _find_potential_src_folders(root: str = ".") -> list[str]:
    """
    Identifies potential source code folders in the given root directory.

    It prioritizes common names like 'src' and the project's root folder name,
    then scans for other directories containing Python files.
    """
    folders = []
    # The current directory's name is often the package name.
    project_name = os.path.basename(os.path.abspath(root))

    # Check for common source folder names first.
    for name in ["src", "app", project_name]:
        if os.path.isdir(name) and name not in folders:
            # Check if it actually contains python files to reduce noise.
            try:
                if any(f.endswith(".py") for f in os.listdir(name)):
                    folders.append(name)
            except OSError:
                continue  # Ignore permission errors

    # Find other directories at the top level that contain .py files.
    for item in os.listdir(root):
        if os.path.isdir(item) and not item.startswith(".") and "venv" not in item:
            if item in folders:
                continue
            try:
                if any(f.endswith(".py") for f in os.listdir(item)):
                    folders.append(item)
            except OSError:
                continue  # Ignore permission errors

    return folders


def _select_src_folder_interactive(folders: list[str]) -> str | None:
    """
    Prompts the user to select their source folder from a list.
    """
    print("\nPlease select your primary source folder from the list below:")
    for i, folder in enumerate(folders):
        print(f"  {i+1}) {folder}")
    print(f"  {len(folders)+1}) [Manual Entry]")
    print(f"  {len(folders)+2}) [Cancel]")

    while True:
        try:
            choice_str = input(f"Enter your choice [1-{len(folders)+2}]: ")
            choice_int = int(choice_str)
            if 1 <= choice_int <= len(folders):
                return folders[choice_int - 1]
            elif choice_int == len(folders) + 1:
                return input("Enter path to your source folder: ")
            elif choice_int == len(folders) + 2:
                return None
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(folders)+2}.")
        except (ValueError, IndexError):
            print("Invalid input. Please enter a number from the list.")


def _generate_pycodetags_toml_section(src_folder: str) -> str:
    """
    Generates the [tool.pycodetags] TOML string with helpful comments.
    """
    return f"""
[tool.pycodetags]
# Source folders to scan for code tags.
# This allows you to run `pycodetags` without specifying the path every time.
src = ["{src_folder}"]

# --- Optional: Common Configurations ---

# Specify Python modules to scan. Useful if your project structure is complex.
# modules = []

# Define which tag schemas are active.
# Default schemas are: todo, fixme, hack, note, perf, bug, question, important
# Example: active_schemas = ["todo", "fixme", "bug"]

# --- Runtime Behavior Control ---
# These settings control pycodetags's behavior when imported in your code.

# Master switch to disable all runtime features (e.g., for production).
# Setting this to true ensures zero performance overhead from the library.
disable_all_runtime_behavior = false

# Enables or disables the runtime actions ('log', 'warn', 'stop').
# If false, runtime checks are silent, even if `disable_all_runtime_behavior` is false.
enable_actions = true

# Default action for runtime checks if a tag doesn't specify one.
# Valid options: "warn", "stop" (raises TypeError), "log", or "nothing".
default_action = "warn"

# Automatically disables all runtime actions when in a CI environment.
# Checks for common CI environment variables (e.g., CI, GITHUB_ACTIONS).
disable_on_ci = true

# Allow pycodetags to load environment variables from a .env file.
use_dot_env = true
"""


def _write_to_pyproject_safe(toml_section: str, pyproject_path: str):
    """
    Safely appends the configuration to pyproject.toml.

    It creates the file if it doesn't exist and adds newlines for separation
    if the file already has content.
    """
    try:
        # Open in append mode, which creates the file if it doesn't exist.
        with open(pyproject_path, "a", encoding="utf-8") as f:
            # f.tell() gives the current position. If > 0, the file is not empty.
            if f.tell() > 0:
                f.write("\n")  # Add a blank line for separation.

            f.write(toml_section.strip())

        print(f"\nSuccessfully configured '[tool.pycodetags]' in {pyproject_path}")
    except OSError as e:
        print(f"\nError: Could not write to {pyproject_path}. {e}")


if __name__ == "__main__":
    # To run this script directly, save it as a .py file (e.g., setup_codetags.py)
    # and run `python setup_codetags.py` in your project's root directory.
    init_pycodetags_config()

```

## File: converters.py

```python
"""
Converters for FolkTag and DataTag typed dicts to DATA class
"""

from __future__ import annotations

import logging
from typing import Any

from pycodetags.data_tags_classes import DATA
from pycodetags.data_tags_methods import promote_fields
from pycodetags.data_tags_schema import DataTag, DataTagSchema
from pycodetags.folk_code_tags import FolkTag

logger = logging.getLogger(__name__)


def convert_folk_tag_to_DATA(folk_tag: FolkTag, schema: DataTagSchema) -> DATA:  # pylint: disable=unused-argument
    """
    Convert a FolkTag to a DATA object. A DATA object does not attempt to
    convert domain specific fields to strongly typed properties/fields

    Args:
        folk_tag (FolkTag): The FolkTag to convert.
        schema (DataTagSchema): Which schema to force the folk tag into
    """
    kwargs = {
        "code_tag": folk_tag.get("code_tag"),
        "custom_fields": folk_tag.get("custom_fields"),
        "comment": folk_tag["comment"],  # required
        "file_path": folk_tag.get("file_path"),
        "line_number": folk_tag.get("line_number"),
        "original_text": folk_tag.get("original_text"),
        "original_schema": "folk",
        "offsets": folk_tag.get("offsets"),
    }
    return DATA(**kwargs)  # type: ignore[arg-type]


def convert_data_tag_to_data_object(tag_value: DataTag, schema: DataTagSchema) -> DATA:
    """
    Convert a DataTag dict to a DATA object.

    Args:
        tag_value (DataTag): The PEP350Tag to convert.
        schema (DataTagSchema): Schema for DataTag
    """
    # default fields should have already been promoted to data_fields by now.
    kwargs = upgrade_to_specific_schema(tag_value, schema)

    return DATA(**kwargs)  # type: ignore[arg-type]


def upgrade_to_specific_schema(tag_value: DataTag, schema: DataTagSchema, flat: bool = True) -> dict[str, Any]:
    """Convert a DataTag to a specific schema.

    Args:
        tag_value (DataTag): The DataTag to convert.
        schema (DataTagSchema): The schema to use for the conversion.
        flat (bool): If True, return a flat dict, otherwise return a nested dict.

    Returns:
        dict[str, Any]: A dictionary representation of the DataTag with fields promoted according to the schema.
    """
    data_fields = tag_value["fields"]["data_fields"]
    custom_fields = tag_value["fields"]["custom_fields"]
    final_data = {}
    final_custom = {}
    for found, value in data_fields.items():
        if found in schema["data_fields"]:
            final_data[found] = value
        else:
            final_custom[found] = value
    for found, value in custom_fields.items():
        if found in schema["data_fields"]:
            if found in final_data:
                logger.warning("Found same field in both data and custom")
            final_data[found] = value
        else:
            if found in final_custom:
                logger.warning("Found same field in both data and custom")
            final_custom[found] = value
    kwargs: DataTag | dict[str, Any] = {
        "code_tag": tag_value["code_tag"],
        "comment": tag_value["comment"],
        # Source Mapping
        "file_path": tag_value.get("file_path"),
        "line_number": tag_value.get("line_number"),
        "original_text": tag_value.get("original_text"),
        "original_schema": "pep350",
        "offsets": tag_value.get("offsets"),
    }
    if flat:
        kwargs["default_fields"] = tag_value["fields"]["default_fields"]  # type:ignore[typeddict-unknown-key]
        kwargs["data_fields"] = final_data  # type:ignore[typeddict-unknown-key]
        kwargs["custom_fields"] = final_custom  # type:ignore[typeddict-unknown-key]
        ud = tag_value["fields"]["unprocessed_defaults"]
        kwargs["unprocessed_defaults"] = ud  # type:ignore[typeddict-unknown-key]
        # kwargs["identity_fields"]=tag_value["fields"].get("identity_fields", {})  # type:ignore[typeddict-unknown-key]
    else:
        kwargs["fields"] = {
            "data_fields": final_data,
            "custom_fields": final_custom,
            "default_fields": tag_value["fields"]["default_fields"],
            "unprocessed_defaults": tag_value["fields"]["unprocessed_defaults"],
            "identity_fields": tag_value["fields"].get("identity_fields", []),
        }
        promote_fields(kwargs, schema)  # type: ignore[arg-type]
    return kwargs  # type: ignore[return-value]

```

## File: data_tags_classes.py

```python
"""
Strongly typed data tags, base for all code tags
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field, fields
from functools import wraps
from typing import Any, Callable, cast  # noqa

from pycodetags import exceptions
from pycodetags.exceptions import ValidationError

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
    line_number: int | None = None
    original_text: str | None = None
    original_schema: str | None = None
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

    def validate_or_raise(self):
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

    def as_data_comment(self) -> str:
        """Print as if it was a PEP-350 comment."""
        the_fields = ""
        to_skip = []

        metadata = [
            "file_path",
            "line_number",
            "original_text",
            "original_schema",
            "offsets",
        ]

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
                        and not key.startswith("_")  # old metadata field
                        and key not in metadata  # new metadata field
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
        if len(complete) > 120:
            first_line += "\n# "
            complete = f"{first_line}<{the_fields.strip()}>"
        return complete

    def __eq__(self, other):
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

    def __repr__(self):
        field_strings = []
        for f in fields(self):
            if f.name != "data_meta" and f.name != "type":
                field_strings.append(f"{f.name}={getattr(self, f.name)!r}")
        return f"{self.__class__.__name__}({', '.join(field_strings)})"

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
                    raise exceptions.PyCodeTagsError("Field in data_fields and custom fields")
                data[key] = value
        if include_comment_and_tag:
            if self.comment:
                data["comment"] = self.comment
            if self.code_tag:
                data["code_tag"] = self.code_tag
        return data

```

## File: data_tags_methods.py

```python
from __future__ import annotations

import datetime
import logging
from typing import Any

from pycodetags.data_tags_schema import DataTag, DataTagSchema

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # noqa

logger = logging.getLogger(__name__)


def promote_fields(tag: DataTag, data_tag_schema: DataTagSchema) -> None:
    fields = tag["fields"]
    if fields["unprocessed_defaults"]:
        for value in fields.get("unprocessed_defaults", []):
            consumed = False
            for the_type, the_name in data_tag_schema["default_fields"].items():
                if the_type == "int" and not fields["data_fields"].get(the_name) and not consumed:
                    try:
                        fields["data_fields"][the_name] = int(value)
                        consumed = True
                    except ValueError:
                        logger.warning(f"Failed to convert {value} to int")
                elif the_type == "date" and not fields["data_fields"].get(the_name) and not consumed:
                    try:
                        fields["data_fields"][the_name] = datetime.datetime.strptime(value, "%Y-%m-%d").date()
                        consumed = True
                    except ValueError:
                        logger.warning(f"Failed to convert {value} to datetime")
                elif the_type == "str" and not fields["data_fields"].get(the_name) and not consumed:
                    fields["data_fields"][the_name] = value
                    consumed = True

    if not fields.get("custom_fields", {}) and not fields.get("default_fields", {}):
        # nothing to promote
        return

    # It is already there, just move it over.
    for default_key, default_value in tag["fields"]["default_fields"].items():
        if default_key in fields["data_fields"] and fields["data_fields"][default_key] != default_value:
            # Strict?
            logger.warning(
                "Field in both data_fields and default_fields and they don't match: "
                f'{default_key}: {fields["data_fields"][default_key]} != {default_value}'
            )

            # # This only handles strongly type DATA() or TODO(). Comment tags are all strings!
            # if isinstance(fields["data_fields"][default_key], list) and isinstance(default_value, list):
            #     fields["data_fields"][default_key].extend(default_value)
            # elif isinstance(fields["data_fields"][default_key], list) and isinstance(default_value, str):
            #     fields["data_fields"][default_key].append(default_value)
            # elif isinstance(fields["data_fields"][default_key], str) and isinstance(default_value, list):
            #     fields["data_fields"][default_key] = default_value + [fields["data_fields"][default_key]]
            # elif isinstance(fields["data_fields"][default_key], str) and isinstance(default_value, str):
            #     # promotes str to list[str], ugly!
            #     fields["data_fields"][default_key] = [fields["data_fields"][default_key], default_value]

        else:
            fields["data_fields"][default_key] = default_value

    # promote a custom_field to root field if it should have been a root field.
    field_aliases: dict[str, str] = data_tag_schema["data_field_aliases"]
    # putative custom field, is it actually standard?
    for custom_field, custom_value in fields["custom_fields"].copy().items():
        if custom_field in field_aliases:
            # Okay, found a custom field that should have been standard
            full_alias = field_aliases[custom_field]

            if fields["data_fields"].get(full_alias):
                # found something already there
                consumed = False
                if isinstance(fields["data_fields"][full_alias], list):
                    # root is list
                    if isinstance(custom_value, list):
                        # both are list: merge list into parent list
                        fields["data_fields"][full_alias].extend(custom_value)
                        consumed = True
                    elif isinstance(custom_value, str):
                        # list/string promote parent string to list (ugh!)
                        fields["data_fields"][full_alias] = fields["data_fields"][full_alias].append(custom_value)
                        consumed = True
                    else:
                        # list/surprise
                        logger.warning(f"Promoting custom_field {full_alias}/{custom_value} to unexpected type")
                        fields["data_fields"][full_alias].append(custom_value)
                        consumed = True
                elif isinstance(fields["data_fields"][full_alias], str):
                    if isinstance(custom_value, list):
                        # str/list: parent str joins custom list
                        fields["data_fields"][full_alias] = [fields["data_fields"][full_alias]] + custom_value
                        consumed = True
                    elif isinstance(custom_value, str):
                        # str/str forms a list
                        fields["data_fields"][full_alias] = [fields["data_fields"][full_alias], custom_value]
                        consumed = True
                    else:
                        # str/surprise
                        logger.warning(f"Promoting custom_field {full_alias}/{custom_value} to unexpected type")
                        fields["data_fields"][full_alias] = [
                            fields["data_fields"][full_alias],
                            custom_value,
                        ]  # xtype: ignore
                        consumed = True
                else:
                    # surprise/surprise = > list
                    logger.warning(f"Promoting custom_field {full_alias}/{custom_value} to unexpected type")
                    fields[full_alias] = [fields[full_alias], custom_value]  # type: ignore
                    consumed = True
                if consumed:
                    del fields["custom_fields"][custom_field]
                else:
                    # This might not  be reachable.
                    logger.warning(f"Failed to promote custom_field {full_alias}/{custom_value}, not consumed")


def merge_two_dicts(x: dict[str, Any], y: dict[str, Any]) -> dict[str, Any]:
    z = x.copy()  # start with keys and values of x
    z.update(y)  # modifies z with keys and values of y
    return z

```

## File: data_tags_parsers.py

```python
"""
Parse specific schemas of data tags
"""

from __future__ import annotations

import logging
import re
from collections.abc import Generator
from pathlib import Path

from pycodetags import folk_code_tags
from pycodetags.comment_finder import find_comment_blocks_from_string
from pycodetags.data_tags_methods import merge_two_dicts, promote_fields
from pycodetags.data_tags_schema import DataTag, DataTagFields, DataTagSchema
from pycodetags.exceptions import SchemaError
from pycodetags.folk_code_tags import FolkTag

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # noqa

logger = logging.getLogger(__name__)


def iterate_comments_from_file(
    file: str, schemas: list[DataTagSchema], include_folk_tags: bool
) -> Generator[DataTag | FolkTag]:
    """
    Collect PEP-350 style code tags from a given file.

    Args:
        file (str): The path to the file to process.
        schemas (DataTaSchema): Schemas that will be detected in file
        include_folk_tags (bool): Include folk schemas that do not strictly follow PEP350

    Yields:
        PEP350Tag: A generator yielding PEP-350 style code tags found in the file.
    """
    logger.info(f"iterate_comments: processing {file}")
    yield from iterate_comments(Path(file).read_text(encoding="utf-8"), Path(file), schemas, include_folk_tags)


def iterate_comments(
    source: str, source_file: Path | None, schemas: list[DataTagSchema], include_folk_tags: bool
) -> Generator[DataTag | FolkTag]:
    """
    Collect PEP-350 style code tags from a given file.

    Args:
        source (str): The source text to process.
        source_file (Path): Where did the source come from
        schemas (DataTaSchema): Schemas that will be detected in file
        include_folk_tags (bool): Include folk schemas that do not strictly follow PEP350

    Yields:
        PEP350Tag: A generator yielding PEP-350 style code tags found in the file.
    """
    if not schemas and not include_folk_tags:
        raise SchemaError("No active schemas, not looking for folk tags. Won't find anything.")
    things: list[DataTag | FolkTag] = []
    for _start_line, _start_char, _end_line, _end_char, final_comment in find_comment_blocks_from_string(source):
        # Can only be one comment block now!
        logger.debug(f"Search for {[_['name'] for _ in schemas]} schema tags")
        found_data_tags = []
        for schema in schemas:
            found_data_tags = parse_codetags(final_comment, schema, strict=False)

            for found in found_data_tags:
                found["file_path"] = str(source_file) if source_file else None
                found["line_number"] = _start_line
                found["original_text"] = final_comment
                found["original_schema"] = "PEP350"
                found["offsets"] = (_start_line, _start_char, _end_line, _end_char)

            if found_data_tags:
                logger.debug(f"Found data tags! : {','.join(_['code_tag'] for _ in found_data_tags)}")
            things.extend(found_data_tags)

        for schema in schemas:
            if not found_data_tags and include_folk_tags and schema["matching_tags"]:
                # BUG: fails if there are two in the same. Blank out consumed text, reconsume bock <matth 2025-07-04
                #  category:parser priority:high status:development release:1.0.0 iteration:1>
                found_folk_tags: list[FolkTag] = []
                # TODO: support config of folk schema.<matth 2025-07-04 category:config priority:high status:development release:1.0.0 iteration:1>
                folk_code_tags.process_text(
                    final_comment,
                    allow_multiline=True,
                    default_field_meaning="assignee",
                    found_tags=found_folk_tags,
                    file_path=str(source_file) if source_file else "",
                    valid_tags=schema["matching_tags"],
                )
                if found_folk_tags:
                    logger.debug(f"Found folk tags! : {','.join(_['code_tag'] for _ in found_folk_tags)}")
                things.extend(found_folk_tags)

    yield from things


def is_int(s: str) -> bool:
    """Check if a string can be interpreted as an integer.
    Args:
        s (str): The string to check.

    Returns:
        bool: True if the string is an integer, False otherwise.

    Examples:
        >>> is_int("123")
        True
        >>> is_int("-456")
        True
        >>> is_int("+789")
        True
        >>> is_int("12.3")
        False
        >>> is_int("abc")
        False
        >>> is_int("")
        False
    """
    if len(s) and s[0] in ("-", "+"):
        return s[1:].isdigit()
    return s.isdigit()


def parse_fields(
    field_string: str, schema: DataTagSchema, strict: bool  # pylint: disable=unused-argument
) -> DataTagFields:
    """
    Parse a field string from a PEP-350 style code tag and return a dictionary of fields.

    Args:
        field_string (str): The field string to parse.
        schema (DataTagSchema): The schema defining the fields and their aliases.
        strict: bool: If True, raises an error if a field appears in multiple places.

    Returns:
        Fields: A dictionary containing the parsed fields.
    """
    legit_names = {}
    for key in schema["data_fields"]:
        legit_names[key] = key
    field_aliases: dict[str, str] = merge_two_dicts(schema["data_field_aliases"], legit_names)

    fields: DataTagFields = {
        "default_fields": {},
        "data_fields": {},
        "custom_fields": {},
        "unprocessed_defaults": [],
        "identity_fields": [],
    }

    # Updated key_value_pattern:
    # - Handles quoted values (single or double) allowing any characters inside.
    # - For unquoted values, it now strictly matches one or more characters that are NOT:
    #   - whitespace `\s`
    #   - single quote `'`
    #   - double quote `"`
    #   - angle bracket `<` (which signals end of field string)
    #   - a comma `,` (unless it's part of a quoted string or explicitly for assignee splitting)
    #   The change here ensures it stops at whitespace, which correctly separates '1' from '2025-06-15'.
    key_value_pattern = re.compile(
        r"""
        ([a-zA-Z_][a-zA-Z0-9_]*) # Key (group 1): alphanumeric key name
        \s*[:=]\s* # Separator (colon or equals, with optional spaces)
        (                        # Start of value group (group 2)
            '(?:[^'\\]|\\.)*' |  # Match single-quoted string (non-greedy, allowing escaped quotes)
            "(?:[^"\\]|\\.)*" |  # Match double-quoted string (non-greedy, allowing escaped quotes)
            (?:[^\s'"<]+)       # Unquoted value: one or more characters not in \s ' " <
        )
        """,
        re.VERBOSE,  # Enable verbose regex for comments and whitespace
    )

    key_value_matches = []
    # Find all key-value pairs in the field_string
    for match in key_value_pattern.finditer(field_string):
        # Store the span (start, end indices) of the match, the key, and the raw value
        key_value_matches.append((match.span(), match.group(1), match.group(2)))

    # Process extracted key-value pairs
    for (_start_idx, _end_idx), key, value_raw in key_value_matches:
        key_lower = key.lower()

        # Strip quotes from the value if it was quoted
        value = value_raw
        if value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        elif value.startswith('"') and value.endswith('"'):
            value = value[1:-1]

        # Assign the parsed value to the appropriate field
        if key_lower in field_aliases:
            normalized_key: str = field_aliases[key_lower]
            if normalized_key == "assignee":
                # Assignees can be comma-separated in unquoted values
                if "assignee" in fields["data_fields"]:
                    fields["data_fields"]["assignee"].extend([v.strip() for v in value.split(",") if v])
                else:
                    fields["data_fields"]["assignee"] = [v.strip() for v in value.split(",") if v]
            else:
                fields["data_fields"][normalized_key] = value
        else:
            # If not a predefined field, add to custom_fields
            fields["custom_fields"][key] = value

    # Extract remaining tokens that were not part of any key-value pair
    consumed_spans = sorted([span for span, _, _ in key_value_matches])

    unconsumed_segments = []
    current_idx = 0
    # Iterate through the field_string to find segments not covered by key-value matches
    for start, end in consumed_spans:
        if current_idx < start:
            # If there's a gap between the last consumed part and the current match, it's unconsumed
            segment = field_string[current_idx:start].strip()
            if segment:  # Only add non-empty segments
                unconsumed_segments.append(segment)
        current_idx = max(current_idx, end)  # Move current_idx past the current consumed area

    # Add any remaining part of the string after the last key-value match
    if current_idx < len(field_string):
        segment = field_string[current_idx:].strip()
        if segment:  # Only add non-empty segments
            unconsumed_segments.append(segment)

    # Join the unconsumed segments and then split by whitespace to get individual tokens
    other_tokens_raw = " ".join(unconsumed_segments)
    other_tokens = [token.strip() for token in other_tokens_raw.split() if token.strip()]

    # Process these remaining tokens for dates (origination_date) and assignees (initials)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")

    # This is too domain specific. Let a plugin handle user aliases.
    # initials_pattern = re.compile(r"^[A-Z,]+$")  # Matches comma-separated uppercase initials

    for token in other_tokens:
        # handles this case:
        # <foo:bar
        #   fizz:buzz
        #  bing:bong>
        if token == "#":  # nosec
            continue
        matched_default = False

        # for default_type, default_key in schema["default_fields"].items():
        # str must go last, it matches everything!
        matched_default = False
        for default_type in ["int", "date", "str", "str|list[str]"]:
            default_key = schema["default_fields"].get(default_type)
            if default_key:
                # Default fields!
                if not matched_default:
                    if default_type == "date" and date_pattern.match(token):
                        # Assign default_key from a standalone date token
                        fields["default_fields"][default_key] = token  # type: ignore[assignment]
                        matched_default = True
                    elif default_type.replace(" ", "") == "str|list[str]":  # initials_pattern.match(token):
                        # Add standalone initials to assignees list
                        if default_key in fields["default_fields"]:
                            fields["default_fields"][default_key].extend([t.strip() for t in token.split(",") if t])
                        else:
                            fields["default_fields"][default_key] = [t.strip() for t in token.split(",") if t]
                        matched_default = True
                    elif default_type == "int" and is_int(token):
                        fields["default_fields"][default_key] = token  # type: ignore[assignment]
                        matched_default = True
                    elif default_type == "str":
                        fields["default_fields"][default_key] = token  # type: ignore[assignment]
                        matched_default = True

        if not matched_default:
            fields["unprocessed_defaults"].append(token)

    return fields


def parse_codetags(text_block: str, data_tag_schema: DataTagSchema, strict: bool) -> list[DataTag]:
    """
    Parse PEP-350 style code tags from a block of text.

    Args:
        text_block (str): The block of text containing PEP-350 style code tags.
        data_tag_schema: DataTagSchema: The schema defining the fields and their aliases.
        strict: bool: If True, raises an error if a field appears in multiple places.

    Returns:
        list[PEP350Tag]: A list of PEP-350 style code tags found in the text block.
    """
    results: list[DataTag] = []
    code_tag_regex = re.compile(
        r"""
        (?P<code_tag>[A-Z\?\!]{3,}) # Code tag (e.g., TODO, FIXME, BUG)
        \s*:\s* # Colon separator with optional whitespace
        (?P<comment>.*?)            # Comment text (non-greedy)
        <                           # Opening angle bracket for fields
        (?P<field_string>.*?)       # Field string (non-greedy)
        >                           # Closing angle bracket for fields
        """,
        re.DOTALL | re.VERBOSE,  # DOTALL allows . to match newlines, VERBOSE allows comments in regex
    )

    matches = list(code_tag_regex.finditer(text_block))
    for match in matches:
        tag_parts = {
            "code_tag": match.group("code_tag").strip(),
            "comment": match.group("comment").strip().rstrip(" \n#"),  # Clean up comment
            "field_string": match.group("field_string")
            .strip()
            .replace("\n", " "),  # Replace newlines in fields with spaces
        }
        fields = parse_fields(tag_parts["field_string"], data_tag_schema, strict)
        results.append(
            {
                "code_tag": tag_parts["code_tag"],
                "comment": tag_parts["comment"],
                "fields": fields,
                "original_text": "N/A",  # BUG: Regex doesn't allow for showing this! <matth 2025-07-04
                # category:parser priority:high status:development release:1.0.0 iteration:1>
            }
        )

    # promote standard fields in custom_fields to root, merging if already exist
    for result in results:
        promote_fields(result, data_tag_schema)
    return results

```

## File: data_tags_schema.py

```python
"""
Abstract data serialization format, of which PEP-350 is one schema.

In scope:
    - parsing a data tag as a data serialization format.
    - defining a schema
    - domain free concepts
    - Parsing python to extract # comments, be it AST or regex or other strategy
    - Round tripping to and from data tag format
    - Equivalence checking by value
    - Merging and promoting fields among default, data and custom.

Out of scope:
    - File system interaction
    - Any particular schema (PEP350 code tags, discussion tags, documentation tags, etc)
    - Domain specific concepts (users, initials, start dates, etc)
    - Docstring style comments and docstrings

Inputs:
    - A block of valid python comment text
    - A schema

Outputs:
    - A python data structure that represents a data structure

Half-hearted goal:
    - Minimize python concepts so this can be implemented in Javascript, etc.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # noqa

logger = logging.getLogger(__name__)


class DataTag(TypedDict, total=False):
    """An abstract data code tag."""

    code_tag: str
    comment: str
    fields: DataTagFields

    # metadata
    file_path: str | None
    line_number: int | None
    original_text: str | None
    original_schema: str | None
    offsets: tuple[int, int, int, int] | None


class DataTagSchema(TypedDict):
    """
    Data for interpreting a domain specific code tag.
    """

    name: str

    matching_tags: list[str]
    """What tag names match, e.g. TODO, FIXME are issue tracker tags"""

    default_fields: dict[str, str]
    """type:name, e.g. str:assignees"""

    data_fields: dict[str, str]
    """name:type, e.g. priority:str"""

    data_field_aliases: dict[str, str]
    """name:alias, e.g. priority:p"""


class DataTagFields(TypedDict):
    """Rules for interpreting the fields part of a code tag"""

    unprocessed_defaults: list[str]

    # When deserializating a field value could appear in default, data and custom field positions.
    default_fields: dict[str, list[Any]]
    """Field without label identified by data type, range or fallback, e.g. user and date"""

    # TODO: support dict[str, int | date | str | list[int, date, str]] ? <matth 2025-07-04
    #  category:schema priority:high status:development release:1.0.0 iteration:1>
    data_fields: dict[str, Any]
    """Expected fields with labels, e.g. category, priority"""

    custom_fields: dict[str, str]
    """Key value pairs, e.g. SAFe program increment number"""

    identity_fields: list[str]
    """Fields which combine to form an identity for the tag, e.g. originator, origination_date"""

```

## File: exceptions.py

```python
class PyCodeTagsError(Exception):
    """Base exception for all PyCodeTags errors."""


class ConfigError(PyCodeTagsError):
    """Exception raised during processing of config file."""


class InvalidActionError(ConfigError):
    """Exception raised during code tag actions."""


class SchemaError(PyCodeTagsError):
    """Exception raised on parsing, etc when situations do not conform to a schema"""


class DataTagParseError(PyCodeTagsError):
    """Parse time exceptions"""


class AggregationError(PyCodeTagsError):
    """Exception when combining many code tags into one stream"""


class ModuleImportError(AggregationError):
    """Exceptions when attempting to import and walk the object graph"""


class SourceNotFoundError(AggregationError):
    """File not found during code tag parsing."""


class PluginError(PyCodeTagsError):
    """Exceptions raised during interaction with pluggy plugin system."""


class PluginLoadError(PluginError):
    """Exceptions raised when first interacting with a plugin"""


class PluginHookError(PluginError):
    """Exceptions raised during hook invocation"""


class FileParsingError(PyCodeTagsError):
    """Exceptions raised while parsing code tags."""


class CommentNotFoundError(FileParsingError):
    """No code tag data found in input source."""


class ValidationError(PyCodeTagsError):
    """Schema or domain dependent problem with code tag data."""

```

## File: folk_code_tags.py

```python
"""
Finds all folk schema tags in source files.

Folk tags roughly follow

# TODO: comment
# TODO(user): comment
# TODO(ticket): comment
# TODO(default_field): Message with domain.com/ticket-123

Optionally

# TODO: Multiline
# comment

Valid tags lists are important for doing looser parsing, e.g. omitting colon, multiline, lowercase etc.

Not sure if I will implement completely loose parsing.
"""

from __future__ import annotations

import logging
import os
import re

from pycodetags.exceptions import SchemaError

try:
    from typing import Literal, TypedDict  # type: ignore[assignment,unused-ignore]
except ImportError:
    from typing_extensions import Literal  # type: ignore[assignment,unused-ignore] # noqa
    from typing_extensions import TypedDict  # noqa


logger = logging.getLogger(__name__)

DefaultFieldMeaning = Literal[
    "person",  # accurate because who knows what that name in parens means
    "assignee",
    "originator",  # compatible with pep350
    "tracker",
]


class FolkTag(TypedDict, total=False):
    """Represents a folk tag found in source code."""

    # data
    code_tag: str
    comment: str
    default_field: str | None
    custom_fields: dict[str, str]

    # data
    file_path: str
    line_number: int
    start_char: int
    offsets: tuple[int, int, int, int]
    original_text: str

    # domain specific
    tracker: str
    assignee: str
    originator: str
    person: str


def folk_tag_to_comment(tag: FolkTag) -> str:
    """Convert a FolkTag to a comment string."""
    people_text = ""
    custom_field_text = ""
    if tag.get("assignee") or tag.get("originator"):
        people = ",".join(_ for _ in (tag.get("assignee", ""), tag.get("originator", "")) if _)
        people.strip(", ")
        if people:
            people_text = f"({people.strip()})"
    if tag["custom_fields"]:

        for key, value in tag["custom_fields"].items():
            custom_field_text += f"{key}={value.strip()} "
        custom_field_text = f"({custom_field_text.strip()}) "

    return f"# {tag['code_tag'].upper()}{people_text}: {custom_field_text}{tag['comment'].strip()}".strip()


def find_source_tags(
    source_path: str,
    valid_tags: list[str] | None = None,
    allow_multiline: bool = False,
    default_field_meaning: DefaultFieldMeaning = "assignee",
) -> list[FolkTag]:
    """
    Finds all folk tags in the source files.

    Args:
        source_path (str): Path to the source file or directory.
        valid_tags (list[str], optional): List of valid code tags to look for. If None, all tags are considered valid.
        allow_multiline (bool, optional): Whether to allow multiline comments. Defaults to False.
        default_field_meaning (DefaultFieldMeaning, optional): Meaning of the default field. Defaults to "assignee".

    Returns:
        list[FolkTag]: A list of FolkTag dictionaries found in the source files.
    """
    if allow_multiline and not valid_tags:
        raise SchemaError("Must include valid tag list if you want to allow multiline comments")

    if not valid_tags:
        valid_tags = []

    if not os.path.exists(source_path):
        raise FileNotFoundError(f"The path '{source_path}' does not exist.")

    if os.path.isfile(source_path):
        files_to_scan = [source_path]
    else:
        files_to_scan = []
        for root, _, files in os.walk(source_path):
            for file in files:
                files_to_scan.append(os.path.join(root, file))

    found_tags: list[FolkTag] = []
    for file_path in files_to_scan:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            text = f.read()

            process_text(text, allow_multiline, default_field_meaning, found_tags, file_path, valid_tags)

    return found_tags


def process_text(
    text: str,
    allow_multiline: bool,
    default_field_meaning: DefaultFieldMeaning,
    found_tags: list[FolkTag],
    file_path: str,
    valid_tags: list[str],
) -> None:
    if "\r\n" in text:
        lines = text.split("\r\n")
    else:
        lines = text.split("\n")

    if len(lines) == 1:
        logger.debug(f"Processing  {file_path}: {lines[0]}")
    else:
        for line in lines:
            logger.debug(f"Processing {file_path} ==>: {line}")
    idx = 0
    while idx < len(lines):
        consumed = process_line(
            file_path,
            found_tags,
            lines,
            idx,
            # schema
            valid_tags,
            allow_multiline,
            default_field_meaning,
        )
        idx += consumed


def extract_first_url(text: str) -> str | None:
    """
    Extracts the first URL from a given text.

    Args:
        text (str): The text to search for URLs.

    Returns:
        str | None: The first URL found in the text, or None if no URL is found.
    """
    # Regex pattern to match URLs with or without scheme
    pattern = r"(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/[^\s]+)"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def process_line(
    file_path: str,
    found_tags: list[FolkTag],
    lines: list[str],
    start_idx: int,
    valid_tags: list[str],
    allow_multiline: bool,
    default_field_meaning: DefaultFieldMeaning,
) -> int:
    """
    Processes a single line to find and parse folk tags.

    Args:
        file_path (str): Path to the source file.
        found_tags (list): List to accumulate found tags.
        lines (list[str]): List of lines in the source file.
        start_idx (int): Index of the line to process.
        valid_tags (list): List of valid code tags to look for.
        allow_multiline (bool): Whether to allow multiline comments.
        default_field_meaning (DefaultFieldMeaning): Meaning of the default field.

    Returns:
        int: Number of lines consumed by this tag.
    """
    if not valid_tags:
        valid_tags = []

    line = lines[start_idx]

    # Match any comment line with an uppercase code_tag
    match = re.match(r"\s*#\s*([A-Z]+)\b(.*)", line)
    if not match:
        return 1

    code_tag_candidate = match.group(1)
    content = match.group(2).strip()

    if valid_tags and code_tag_candidate not in valid_tags:
        return 1

    # Clean colon if present
    if content.startswith(":"):
        content = content[1:].lstrip()

    # Offset tracking: start
    start_line = start_idx
    start_char = line.find(f"# {code_tag_candidate}")

    # Multiline handling
    current_idx = start_idx
    if allow_multiline and valid_tags:
        multiline_content = [content]
        next_idx = current_idx + 1
        while next_idx < len(lines):
            next_line = lines[next_idx].strip()
            if next_line.startswith("#") and not any(re.match(rf"#\s*{t}\b", next_line) for t in valid_tags):
                multiline_content.append(next_line.lstrip("# "))
                next_idx += 1
            else:
                break
        content = " ".join(multiline_content)
        end_line = next_idx - 1
        end_char = len(lines[end_line])
        consumed_lines = next_idx - start_idx
    else:
        end_line = start_idx
        end_char = len(line)
        consumed_lines = 1

    # Field parsing
    default_field = None
    custom_fields = {}
    comment = content

    field_match = re.match(r"\(([^)]*)\):(.*)", content)
    if field_match:
        field_section = field_match.group(1).strip()
        comment = field_match.group(2).strip()

        for part in field_section.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                key, val = part.split("=", 1)
                custom_fields[key.strip()] = val.strip()
            else:
                if default_field is None:
                    default_field = part
                else:
                    default_field += ", " + part
    else:
        id_match = re.match(r"(\d+):(.*)", content)
        if id_match:
            default_field = id_match.group(1)
            comment = id_match.group(2).strip()

    # Construct the tag
    found_tag: FolkTag = {
        "file_path": file_path,
        "line_number": start_idx + 1,
        "start_char": start_char,
        "code_tag": code_tag_candidate,
        "default_field": default_field,
        "custom_fields": custom_fields,
        "comment": comment,
        "original_text": content,
        "offsets": (start_line, start_char, end_line, end_char),
    }

    if default_field and default_field_meaning:
        found_tag[default_field_meaning] = default_field

    url = extract_first_url(comment)
    if url:
        found_tag["tracker"] = url

    # TODO: decide if heuristics like length are better than an explicit list or explicit : to end tag <matth 2025-07-04
    #  category:parser status:development priority:low release:1.0.0 iteration:1>
    if len(code_tag_candidate) > 1:
        found_tags.append(found_tag)

    return consumed_lines

```

## File: logging_config.py

```python
"""
Logging configuration.
"""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    import colorlog  # noqa

    # This is only here so that I can see if colorlog is installed
    # and to keep autofixers from removing an "unused import"
    if False:  # pylint: disable=using-constant-test
        assert colorlog  # noqa # nosec
    colorlog_available = True
except ImportError:  # no qa
    colorlog_available = False


def generate_config(level: str = "DEBUG", enable_bug_trail: bool = False) -> dict[str, Any]:
    """
    Generate a logging configuration.
    Args:
        level: The logging level.
        enable_bug_trail: Whether to enable bug trail logging.

    Returns:
        dict: The logging configuration.
    """
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "standard": {"format": "[%(levelname)s] %(name)s: %(message)s"},
            "colored": {
                "()": "colorlog.ColoredFormatter",
                "format": "%(log_color)s%(levelname)-8s%(reset)s %(green)s%(message)s",
            },
        },
        "handlers": {
            "default": {
                "level": level,
                "formatter": "colored",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",  # Default is stderr
            },
        },
        "loggers": {
            "pycodetags": {
                "handlers": ["default"],
                "level": level,
                "propagate": False,
            }
        },
    }
    if not colorlog_available:
        del config["formatters"]["colored"]
        config["handlers"]["default"]["formatter"] = "standard"

    if os.environ.get("NO_COLOR") or os.environ.get("CI"):
        config["handlers"]["default"]["formatter"] = "standard"

    if enable_bug_trail:
        try:
            # pylint: disable=import-outside-toplevel
            import bug_trail_core
        except ImportError:
            print("bug_trail_core is not installed, skipping bug trail handler configuration.")
            return config

        section = bug_trail_core.read_config(config_path="pyproject.toml")
        # handler = bug_trail_core.BugTrailHandler(section.database_path, minimum_level=logging.DEBUG)
        config["handlers"]["bugtrail"] = {
            "class": "bug_trail_core.BugTrailHandler",
            "db_path": section.database_path,
            "minimum_level": logging.DEBUG,
        }
        config["loggers"]["pycodetags"]["handlers"].append("bugtrail")

    return config

```

## File: plugin_diagnostics.py

```python
"""
Tool for plugin developers
"""

import pluggy


def plugin_currently_loaded(pm: pluggy.PluginManager) -> None:
    """List plugins in memory"""
    print("--- Loaded pycodetags Plugins ---")
    loaded_plugins = pm.get_plugins()  #
    if not loaded_plugins:
        print("No plugins currently loaded.")
    else:
        for plugin in loaded_plugins:
            plugin_name = pm.get_canonical_name(plugin)  #
            blocked_status = " (BLOCKED)" if pm.is_blocked(plugin_name) else ""  #
            print(f"- {plugin_name}{blocked_status}")

            # Optional: print more detailed info about hooks implemented by this plugin
            # For each hookspec, list if this plugin implements it
            for hook_name in pm.hook.__dict__:
                if hook_name.startswith("_"):  # Skip internal attributes
                    continue
                hook_caller = getattr(pm.hook, hook_name)
                if (
                    plugin in hook_caller.get_hookimpls()
                ):  # Check if this specific plugin has an implementation for this hook
                    print(f"  - Implements hook: {hook_name}")

    print("------------------------------")

```

## File: plugin_manager.py

```python
"""
The pluggy plugin manager that finds plugins and invokes them when needed.
"""

import logging

import pluggy

from pycodetags.plugin_specs import CodeTagsSpec

logger = logging.getLogger(__name__)

PM = pluggy.PluginManager("pycodetags")
PM.add_hookspecs(CodeTagsSpec)
# PM.set_blocked("malicious_plugin")
PLUGIN_COUNT = PM.load_setuptools_entrypoints("pycodetags")
logger.info(f"Found {PLUGIN_COUNT} plugins")


def reset_plugin_manager() -> None:
    """For testing or events can double up"""
    # pylint: disable=global-statement
    global PM  # nosec # noqa
    PM = pluggy.PluginManager("pycodetags")
    PM.add_hookspecs(CodeTagsSpec)
    PM.load_setuptools_entrypoints("pycodetags")


if logger.isEnabledFor(logging.DEBUG):
    # magic line to set a writer function
    PM.trace.root.setwriter(print)
    undo = PM.enable_tracing()


# At class level or module-level:
def get_plugin_manager() -> pluggy.PluginManager:
    """Interface to help with unit testing"""
    return PM

```

## File: plugin_specs.py

```python
"""
Pluggy supports
"""

from __future__ import annotations

# pylint: disable=unused-argument
import argparse
from collections.abc import Callable

import pluggy

from pycodetags.config import CodeTagsConfig
from pycodetags.data_tags_classes import DATA
from pycodetags.data_tags_schema import DataTag, DataTagSchema
from pycodetags.folk_code_tags import FolkTag

hookspec = pluggy.HookspecMarker("pycodetags")


class CodeTagsSpec:
    """A hook specification namespace for pycodetags."""

    @hookspec
    def register_app(self, pm: pluggy.PluginManager, parser: argparse.ArgumentParser) -> bool:
        """Register a plugin that acts like an app with its own plugins and cli commands."""
        return False

    @hookspec
    def print_report(self, format_name: str, found_data: list[DATA], output_path: str, config: CodeTagsConfig) -> bool:
        """
        Allows plugins to define new output report formats.

        Args:
            format_name: The name of the report format to print.
            found_data: The list[DATA] data to be printed.
            output_path: The path where the report should be saved.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            bool: True if the plugin handled the report printing, False otherwise.
        """
        return False

    @hookspec
    def print_report_style_name(self) -> list[str]:
        """
        Allows plugins announce report format names.

        Returns:
            List of supported format
        """
        return []

    @hookspec
    def add_cli_subcommands(self, subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
        """
        Allows plugins to add new subcommands to the pycodetags CLI.

        Args:
            subparsers (argparse._SubParsersAction): The ArgumentParser subparsers object to add subcommands to.
        """

    @hookspec
    def run_cli_command(
        self,
        command_name: str,
        args: argparse.Namespace,
        found_data: Callable[[DataTagSchema], list[DATA]],
        config: CodeTagsConfig,
    ) -> bool:
        """
        Allows plugins to handle the execution of their registered CLI commands.

        Args:
            command_name: The name of the command to run.
            args: The parsed arguments for the command.
            found_data: The list[DATA] data to be processed.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            bool: True if the command was handled by the plugin, False otherwise.
        """
        return False

    @hookspec
    def validate(self, item: DataTag, config: CodeTagsConfig) -> list[str]:
        """
        Allows plugins to add custom validation logic to TODO items.

        Args:
            item: The TODO item to validate.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            List of validation error messages.
        """
        return []

    @hookspec
    def find_source_tags(self, already_processed: bool, file_path: str, config: CodeTagsConfig) -> list[FolkTag]:
        """
        Allows plugins to provide folk-style code tag parsing for non-Python source files.

        Args:
            already_processed: first pass attempt to find all tags. Be careful of duplicates.
            file_path: The path to the source file.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            A list of FolkTag dictionaries.
        """
        return []

    @hookspec
    def file_handler(self, already_processed: bool, file_path: str, config: CodeTagsConfig) -> bool:
        """
        Allows plugins to do something with source file.

        Args:
            already_processed: Indicates if the file has been processed before.
            file_path: The path to the source file.
            config: The CodeTagsConfig instance containing configuration settings.

        Returns:
            True if file processed by plugin
        """
        return False

```

## File: pure_data_schema.py

```python
"""
The domain-free schema.

When used, all fields are parsed as custom fields.
"""

from pycodetags.data_tags_schema import DataTagSchema

PureDataSchema: DataTagSchema = {
    "name": "DATA",
    "matching_tags": ["DATA"],
    "default_fields": {
        # No defaults, no domain!
    },
    "data_fields": {
        # No domain fields, pure data!
    },
    "data_field_aliases": {
        # No alias, no domain!
    },
}

```

## File: views.py

```python
"""
Given data structure returned by collect submodule, creates human-readable reports.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pycodetags.data_tags_classes import DATA
from pycodetags.view_tools import group_and_sort

logger = logging.getLogger(__name__)


def print_validate(found: list[DATA]) -> None:
    """
    Prints validation errors for TODOs.

    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    for item in sorted(found, key=lambda x: x.code_tag or ""):
        validations = item.validate()
        if validations:
            print(item.as_data_comment())
            print(item.terminal_link())
            for validation in validations:
                print(f"  {validation}")
                print(f"Original Schema {item.original_schema}")
                print(f"Original Text {item.original_schema}")

            print()


def print_html(found: list[DATA]) -> None:
    """
    Prints TODOs and Dones in a structured HTML format.

    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    tags = set()
    for todo in found:
        tags.add(todo.code_tag)

    for tag in tags:
        for todo in found:
            # TODO: find more efficient way to filter.<matth 2025-07-04 priority:low category:views
            #  status:development release:1.0.0 iteration:1>
            if todo.code_tag == tag:
                print(f"<h1>{tag}</h1>")
                print("<ul>")
                print(f"<li><strong>{todo.comment}</strong><br>{todo.data_fields}</li>")
                print("</ul>")


def print_text(found: list[DATA]) -> None:
    """
    Prints TODOs and Dones in text format.
    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    todos = found
    if todos:
        grouped = group_and_sort(
            todos, key_fn=lambda x: x.code_tag or "N/A", sort_items=True, sort_key=lambda x: x.comment or "N/A"
        )
        for tag, items in grouped.items():
            print(f"--- {tag.upper()} ---")
            for todo in items:
                print(todo.as_data_comment())
                print()
    else:
        print("No Code Tags found.")


def print_json(found: list[DATA]) -> None:
    """
    Prints TODOs and Dones in a structured JSON format.
    Args:
        found (list[DATA]): The collected TODOs and Dones.
    """
    todos = found

    output = [t.to_dict() for t in todos]

    def default(o: Any) -> str:
        if hasattr(o, "data_meta"):
            o.data_meta = None

        return json.dumps(o.to_dict()) if hasattr(o, "to_dict") else str(o)

    print(json.dumps(output, indent=2, default=default))


def print_data_md(found: list[DATA]) -> None:
    """
    Outputs DATA items in a markdown format.

    """
    # pylint:disable=protected-access
    grouped = group_and_sort(found, lambda _: "" if not _.file_path else _.file_path, sort_items=False)
    for file, items in grouped.items():
        print(file)
        print("```python")
        for item in items:
            print(item.as_data_comment())
            print()
        print("```")
        print()


def print_summary(found: list[DATA]) -> None:
    """
    Prints a summary count of code tags (e.g., TODO, DONE) from found DATA items.

    Args:
        found (list[DATA]): The collected TODOs and DONEs.
    """
    from collections import Counter

    tag_counter = Counter(tag.code_tag or "UNKNOWN" for tag in found)

    if not tag_counter:
        print("No code tags found.")
        return

    print("Code Tag Summary:")
    for tag, count in sorted(tag_counter.items()):
        print(f"{tag.upper()}: {count}")

```

## File: view_tools.py

```python
"""
Like itertools, this is the functional programming code for list[TODO]
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable  # noqa


def group_and_sort(
    items: list[Any],
    key_fn: Callable[[Any], str],
    sort_items: bool = True,
    sort_key: Callable[[Any], Any] | None = None,
) -> dict[str, list[Any]]:
    """
    Groups and optionally sorts a list of items by a key function.

    Args:
        items: The list of items to group.
        key_fn: A function that returns the grouping key for an item.
        sort_items: Whether to sort the items within each group.
        sort_key: A custom sort key function for sorting items in each group.

    Returns:
        A dictionary mapping keys to lists of items.
        Keys with None or empty values are grouped under '(unlabeled)'.
    """
    grouped: dict[str, list[Any]] = defaultdict(list)

    for item in items:
        raw_key = key_fn(item)
        norm_key = str(raw_key).strip().lower() if raw_key else "(unlabeled)"
        grouped[norm_key].append(item)

    if sort_items:
        for norm_key, group in grouped.items():
            try:
                grouped[norm_key] = sorted(group, key=sort_key or key_fn)
            except Exception as e:
                raise ValueError(f"Failed to sort group '{norm_key}': {e}") from e

    return dict(sorted(grouped.items(), key=lambda x: x[0]))

```

## File: __about__.py

```python
"""Metadata for pycodetags."""

__all__ = [
    "__title__",
    "__version__",
    "__description__",
    "__readme__",
    "__keywords__",
    "__license__",
    "__requires_python__",
    "__status__",
]

__title__ = "pycodetags"
__version__ = "0.3.0"
__description__ = "TODOs in source code as a first class construct, follows PEP350"
__readme__ = "README.md"
__keywords__ = ["pep350", "pep-350", "codetag", "codetags", "code-tags", "code-tag", "TODO", "FIXME", "pycodetags"]
__license__ = "MIT"
__requires_python__ = ">=3.7"
__status__ = "4 - Beta"

```

## File: __init__.py

```python
"""
Code Tags is a tool and library for working with TODOs into source code.

Only the strongly typed decorators, exceptions and context managers are exported.

Everything else is a plugin.
"""

__all__ = [
    # Data tag support
    "DATA",
    "DataTag",
    "DataTagSchema",
    "PureDataSchema",
    # Serialization interfaces
    "dumps",
    "dump",
    "dump_all",
    "dumps_all",
    # Deserialization interfaces
    "loads",
    "load",
    "load_all",
    "loads_all",
    # Plugin interfaces
    "CodeTagsSpec",
]

from pycodetags.common_interfaces import dump, dump_all, dumps, dumps_all, load, load_all, loads, loads_all
from pycodetags.data_tags_classes import DATA
from pycodetags.data_tags_schema import DataTag, DataTagSchema
from pycodetags.plugin_specs import CodeTagsSpec
from pycodetags.pure_data_schema import PureDataSchema

```

## File: __main__.py

```python
"""
CLI for pycodetags.
"""

from __future__ import annotations

import argparse
import logging
import logging.config
import sys
from collections.abc import Sequence

import pluggy

import pycodetags.__about__ as __about__
import pycodetags.pure_data_schema as pure_data_schema
from pycodetags.aggregate import aggregate_all_kinds_multiple_input
from pycodetags.config import CodeTagsConfig, get_code_tags_config
from pycodetags.config_init import init_pycodetags_config
from pycodetags.data_tags_classes import DATA
from pycodetags.data_tags_schema import DataTagSchema
from pycodetags.exceptions import CommentNotFoundError
from pycodetags.logging_config import generate_config
from pycodetags.plugin_diagnostics import plugin_currently_loaded
from pycodetags.plugin_manager import get_plugin_manager
from pycodetags.utils import load_dotenv
from pycodetags.views import print_html, print_json, print_summary, print_text, print_validate


class InternalViews:
    """Register internal views as a plugin"""

    @pluggy.HookimplMarker("pycodetags")
    def print_report(self, format_name: str, found_data: list[DATA]) -> bool:
        """
        Internal method to handle printing of reports in various formats.

        Args:
            format_name (str): The name of the format requested by the user.
            found_data (list[DATA]): The data collected from the source code.

        Returns:
            bool: True if the format was handled, False otherwise.
        """
        if format_name == "text":
            print_text(found_data)
            return True
        if format_name == "html":
            print_html(found_data)
            return True
        if format_name == "json":
            print_json(found_data)
            return True
        if format_name == "summary":
            print_summary(found_data)
            return True
        return False


def main(argv: Sequence[str] | None = None) -> int:
    """
    Main entry point for the pycodetags CLI.

    Args:
        argv (Sequence[str] | None): Command line arguments. If None, uses sys.argv.
    """
    pm = get_plugin_manager()

    pm.register(InternalViews())
    # --- end pluggy setup ---

    parser = argparse.ArgumentParser(
        description=f"{__about__.__description__} (v{__about__.__version__})",
        epilog="Install pycodetags-issue-tracker plugin for TODO tags. ",
    )
    common_switches(parser)

    # Basic arguments that apply to all commands (like verbose/info/bug-trail/config)
    base_parser = argparse.ArgumentParser(add_help=False)
    common_switches(base_parser)
    # validate switch
    base_parser.add_argument("--validate", action="store_true", help="Validate all the items found")

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("init", parents=[base_parser], help="Initialize domain-free config")

    # 'report' command
    report_parser = subparsers.add_parser("data", parents=[base_parser], help="Generate code tag reports")

    # report runs collectors, collected things can be validated
    report_parser.add_argument("--module", action="append", help="Python module to inspect (e.g., 'my_project.main')")
    report_parser.add_argument("--src", action="append", help="file or folder of source code")

    report_parser.add_argument("--output", help="destination file or folder")

    extra_supported_formats = []
    for result in pm.hook.print_report_style_name():
        extra_supported_formats.extend(result)

    supported_formats = list(set(["text", "html", "json", "summary"] + extra_supported_formats))

    report_parser.add_argument(
        "--format",
        choices=supported_formats,
        default="text",
        help="Output format for the report.",
    )
    # report_parser.add_argument("--validate", action="store_true", help="Validate all the items found")

    _plugin_info_parser = subparsers.add_parser(
        "plugin-info", parents=[base_parser], help="Display information about loaded plugins"
    )

    # Allow plugins to add their own subparsers
    new_subparsers = pm.hook.add_cli_subcommands(subparsers=subparsers)
    # Hack because we don't want plugins to have to wire up the basic stuff
    for new_subparser in new_subparsers:
        common_switches(new_subparser)
        # validate switch
        new_subparser.add_argument("--validate", action="store_true", help="Validate all the items found")

    args = parser.parse_args(args=argv)

    if hasattr(args, "config") and args.config:
        code_tags_config = CodeTagsConfig(pyproject_path=args.config)
    else:
        code_tags_config = CodeTagsConfig()

    if code_tags_config.use_dot_env():
        load_dotenv()

    verbose = hasattr(args, "verbose") and args.verbose
    info = hasattr(args, "info") and args.info
    bug_trail = hasattr(args, "bug_trail") and args.bug_trail

    if verbose:
        config = generate_config(level="DEBUG", enable_bug_trail=bug_trail)
        logging.config.dictConfig(config)
    elif info:
        config = generate_config(level="INFO", enable_bug_trail=bug_trail)
        logging.config.dictConfig(config)
    else:
        # Essentially, quiet mode
        config = generate_config(level="FATAL", enable_bug_trail=bug_trail)
        logging.config.dictConfig(config)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "init":
        init_pycodetags_config()
        return 0

    # Handle the 'report' command
    if args.command in ("report", "data"):
        modules = args.module or code_tags_config.modules_to_scan()
        src = args.src or code_tags_config.source_folders_to_scan()

        if not modules and not src:
            print(
                "Need to specify one or more importable modules (--module) "
                "or source code folders/files (--src) or specify in config file.",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            found = aggregate_all_kinds_multiple_input(modules, src, pure_data_schema.PureDataSchema)

        except ImportError:
            print(f"Error: Could not import module(s) '{args.module}'", file=sys.stderr)
            return 1

        if args.validate:
            if len(found) == 0:
                raise CommentNotFoundError("No data to validate.")
            print_validate(found)
        else:
            if len(found) == 0:
                raise CommentNotFoundError("No data to report.")
            # Call the hook.
            results = pm.hook.print_report(
                format_name=args.format, output_path=args.output, found_data=found, config=get_code_tags_config()
            )
            if not any(results):
                print(f"Error: Format '{args.format}' is not supported.", file=sys.stderr)
                return 1
                # --- NEW: Handle 'plugin-info' command ---
    elif args.command == "plugin-info":
        plugin_currently_loaded(pm)
    else:
        # Pass control to plugins for other commands
        # Aggregate data if plugins might need it
        if hasattr(args, "module") and args.module:
            modules = getattr(args, "module", [])
        else:
            modules = code_tags_config.modules_to_scan()

        if hasattr(args, "src") and args.src:
            src = getattr(args, "src", [])
        else:
            src = code_tags_config.source_folders_to_scan()

        def found_data_for_plugins_callback(schema: DataTagSchema) -> list[DATA]:
            return source_and_modules_searcher(args.command, modules, src, schema)

        handled_by_plugin = pm.hook.run_cli_command(
            command_name=args.command,
            args=args,
            found_data=found_data_for_plugins_callback,
            config=get_code_tags_config(),
        )
        if not any(handled_by_plugin):
            print(f"Error: Unknown command '{args.command}'.", file=sys.stderr)
            return 1
    return 0


def source_and_modules_searcher(command: str, modules: list[str], src: list[str], schema: DataTagSchema) -> list[DATA]:
    try:
        all_found: list[DATA] = []
        for source in src:
            found_tags = aggregate_all_kinds_multiple_input([""], [source], schema)
            all_found.extend(found_tags)
        more_found = aggregate_all_kinds_multiple_input(modules, [], schema)
        all_found.extend(more_found)
        found_data_for_plugins = all_found
    except ImportError:
        logging.warning(f"Could not aggregate data for command {command}, proceeding without it.")
        found_data_for_plugins = []
    return found_data_for_plugins


def common_switches(parser) -> None:
    parser.add_argument("--config", help="Path to config file, defaults to current folder pyproject.toml")
    parser.add_argument("--verbose", default=False, action="store_true", help="verbose level logging output")
    parser.add_argument("--info", default=False, action="store_true", help="info level logging output")
    parser.add_argument("--bug-trail", default=False, action="store_true", help="enable bug trail, local logging")


if __name__ == "__main__":
    sys.exit(main())

```

## File: utils\cache_utils.py

```python
"""
A zero-dependency, persistent, file-system-based memoization decorator for Python.

This module provides a decorator that caches the results of function calls on the
filesystem. This allows the cache to persist across multiple executions of a script,
making it ideal for CLI tools or build processes that repeatedly process the same data.

Features:
- Zero external dependencies (uses only the Python standard library).
- Caches are stored in a `.pycodetags_cache` directory by default.
- Automatically locates the project root by searching for a `pyproject.toml` file.
- Cache directory can be overridden for testing or custom configurations.
- Automatically creates a .gitignore file in the cache directory.
- Provides a `clear_cache` function to purge all cache items on demand.
- Optional gzip compression for cache files to save disk space.
- Stale cache entries are automatically removed based on a configurable TTL.
- Cache keys are generated from the function's name and arguments, supporting
  various argument types including complex objects.
- Handles potential race conditions and corrupted cache files gracefully.
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import pickle  # nosec
import shutil
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# Define a generic TypeVar for annotating the decorated function's return type.
F = TypeVar("F", bound=Callable[..., Any])

# A global flag to ensure the cache cleanup logic runs only once per process.
_CACHE_CLEANUP_PERFORMED: dict[str, bool] = {}


def _get_cache_dir(cache_dir_override: Path | None = None) -> Path:
    """
    Determines the correct cache directory path.

    Uses the override if provided, otherwise searches for the project root.
    """
    if cache_dir_override:
        return cache_dir_override

    current_path = Path.cwd().resolve()
    for parent in [current_path] + list(current_path.parents):
        if (parent / "pyproject.toml").is_file():
            return parent / ".pycodetags_cache"

    raise FileNotFoundError(
        "Could not find project root. The 'persistent_memoize' decorator requires "
        "a 'pyproject.toml' file to determine the cache location, or you must "
        "provide a 'cache_dir_override'."
    )


def clear_cache(cache_dir_override: Path | None = None) -> None:
    """
    Deletes all items in the cache directory, except for the .gitignore file.

    Args:
        cache_dir_override: Specify the cache directory to clear. If None, it
                            will be determined automatically by looking for
                            pyproject.toml.
    """
    try:
        cache_dir = _get_cache_dir(cache_dir_override)
        if not cache_dir.is_dir():
            print(f"Cache directory {cache_dir} does not exist. Nothing to clear.")
            return

        for item in cache_dir.iterdir():
            try:
                if item.name == ".gitignore":
                    continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except OSError as e:
                print(f"Warning: Could not remove cache item {item}. Error: {e}")
        print(f"Cache cleared successfully at {cache_dir}.")
    except (FileNotFoundError, OSError) as e:
        print(f"Error clearing cache: {e}")


def persistent_memoize(
    ttl_seconds: int = 86400,
    cache_dir_override: Path | None = None,
    use_gzip: bool = False,
    raise_on_missing_config: bool = False,
) -> Callable[[F], F]:
    """
    A decorator factory for filesystem-based memoization.

    Args:
        ttl_seconds: The time-to-live for cache entries, in seconds.
                     Defaults to 86400 (24 hours).
        cache_dir_override: An optional Path object to specify the cache
                            directory, bypassing project root detection.
                            Ideal for unit tests.
        use_gzip: If True, compresses cache files using gzip. This can save
                  significant disk space but adds a small CPU overhead.
                  Defaults to False.
        raise_on_missing_config: Raise exception if pyproject.toml not found.

    Returns:
        A decorator that can be applied to a function.
    """
    global _CACHE_CLEANUP_PERFORMED

    try:
        cache_dir = _get_cache_dir(cache_dir_override)
        cache_dir.mkdir(exist_ok=True)

        # Ensure the cache directory is ignored by git
        gitignore_path = cache_dir / ".gitignore"
        if not gitignore_path.exists():
            with gitignore_path.open("w") as f:
                f.write("*\n")

    except (FileNotFoundError, OSError) as e:
        print(f"Warning: Persistent memoization disabled. Reason: {e}")
        if raise_on_missing_config:
            raise FileNotFoundError(
                "Persistent memoization requires a 'pyproject.toml' file to determine "
                "the cache location, or you must provide a 'cache_dir_override'."
            ) from e

        def no_op_decorator(func: F) -> F:
            return func

        return no_op_decorator

    # --- Stale Cache Cleanup (runs once per session per cache_dir) ---
    cache_dir_str = str(cache_dir)
    if not _CACHE_CLEANUP_PERFORMED.get(cache_dir_str):
        now = time.time()
        try:
            for cache_file in cache_dir.iterdir():
                if cache_file.is_file() and cache_file.name != ".gitignore":
                    try:
                        modification_time = cache_file.stat().st_mtime
                        if (now - modification_time) > ttl_seconds:
                            cache_file.unlink()
                    except OSError:
                        pass
        except OSError as e:
            print(f"Warning: Could not perform cache cleanup. Error: {e}")
        _CACHE_CLEANUP_PERFORMED[cache_dir_str] = True

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                key_data = pickle.dumps((args, sorted(kwargs.items())))
            except Exception:
                return func(*args, **kwargs)

            hasher = hashlib.sha256()
            hasher.update(func.__qualname__.encode("utf-8"))
            hasher.update(key_data)

            extension = ".pkl.gz" if use_gzip else ".pkl"
            cache_filename = f"{hasher.hexdigest()}{extension}"
            cache_filepath = cache_dir / cache_filename

            if cache_filepath.is_file() and (time.time() - cache_filepath.stat().st_mtime) < ttl_seconds:
                try:
                    open_func = gzip.open if use_gzip else open
                    with open_func(cache_filepath, "rb") as f:
                        return pickle.load(f)  # nosec
                except (pickle.UnpicklingError, EOFError, OSError, gzip.BadGzipFile) as e:
                    print(f"Warning: Could not read cache file {cache_filepath}. Recomputing. Error: {e}")

            result = func(*args, **kwargs)
            try:
                open_func = gzip.open if use_gzip else open
                with open_func(cache_filepath, "wb") as f:
                    pickle.dump(result, f)
            except OSError as e:
                print(f"Warning: Could not write to cache file {cache_filepath}. Error: {e}")

            return result

        return wrapper  # type: ignore

    return decorator


# # --- Example Usage ---
# if __name__ == '__main__':
#     # # Create a dummy pyproject.toml for demonstration
#     # if not Path('pyproject.toml').exists():
#     #     Path('pyproject.toml').touch()
#
#     @persistent_memoize(ttl_seconds=20, use_gzip=True)
#     def slow_gzipped_op(data: dict) -> dict:
#         """A dummy function that simulates a slow operation with gzip."""
#         print(f"Executing slow_gzipped_op for data: {str(data)[:20]}...")
#         time.sleep(2)
#         result = {**data, "processed_at": time.time()}
#         print("...Gzipped operation complete.")
#         return result
#
#     print("--- Gzip Test: First Run (Slow) ---")
#     start_time = time.time()
#     res1 = slow_gzipped_op({"id": 123, "payload": "a" * 100})
#     print(f"Result 1: 'processed_at': {res1['processed_at']}")
#     print(f"Time taken: {time.time() - start_time:.2f}s\n")
#
#     print("--- Gzip Test: Second Run (Fast, from cache) ---")
#     start_time = time.time()
#     res2 = slow_gzipped_op({"id": 123, "payload": "a" * 100})
#     print(f"Result 2: 'processed_at': {res2['processed_at']}")
#     print(f"Time taken: {time.time() - start_time:.2f}s\n")
#
#     assert res1['processed_at'] == res2['processed_at']
#     print("Timestamps match, confirming cache was used.")
#
#     print("\n--- Cache Clearing Test ---")
#     print("Calling clear_cache()...")
#     clear_cache()
#
#     print("\n--- Gzip Test: Third Run (Slow again, after clearing cache) ---")
#     start_time = time.time()
#     res3 = slow_gzipped_op({"id": 123, "payload": "a" * 100})
#     print(f"Result 3: 'processed_at': {res3['processed_at']}")
#     print(f"Time taken: {time.time() - start_time:.2f}s\n")
#
#     assert res1['processed_at'] != res3['processed_at']
#     print("Timestamp is new, confirming cache was cleared and value was recomputed.")

```

## File: utils\dotenv.py

```python
"""
.env file support to avoid another dependency.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _strip_inline_comment(value: str) -> str:
    """Strip unquoted inline comments starting with '#'."""
    result = []
    in_single = in_double = False

    for i, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            logger.debug(f"Stripping inline comment starting at index {i}")
            break
        result.append(char)
    return "".join(result).strip()


def _unquote(value: str) -> str:
    """Remove surrounding quotes from a string if they match."""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def load_dotenv(file_path: Path | None = None) -> None:
    """Load environment variables from a .env file into os.environ.

    Args:
        file_path (Optional[Path]): Optional custom path to a .env file.
            If not provided, defaults to ".env" in the current working directory.

    Notes:
        - Lines that are blank, comments (starting with #), or shebangs (#!) are ignored.
        - Lines must be in the form of `KEY=VALUE` or `export KEY=VALUE`.
        - Existing environment variables will not be overwritten.
        - Inline comments (starting with unquoted #) are stripped.
        - Quoted values are unwrapped.
    """
    if file_path is None:
        file_path = Path.cwd() / ".env"

    logger.info(f"Looking for .env file at: {file_path}")

    if not file_path.exists():
        logger.info(f".env file not found at: {file_path}")
        return

    logger.info(".env file found. Starting to parse...")

    with file_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            original_line = line.rstrip("\n")
            line = line.strip()

            logger.debug(f"Line {line_number}: '{original_line}'")

            if not line or line.startswith("#") or line.startswith("#!") or line.startswith("!/"):
                logger.debug(f"Line {line_number} is blank, a comment, or a shebang. Skipping.")
                continue

            if line.startswith("export "):
                line = line[len("export ") :].strip()

            if "=" not in line:
                logger.warning(f"Line {line_number} is not a valid assignment. Skipping: '{original_line}'")
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                logger.warning(f"Line {line_number} has empty key. Skipping: '{original_line}'")
                continue

            value = _strip_inline_comment(value)
            value = _unquote(value)

            if key in os.environ:
                logger.info(f"Line {line_number}: Key '{key}' already in os.environ. Skipping.")
                continue

            os.environ[key] = value
            logger.info(f"Line {line_number}: Loaded '{key}' = '{value}'")


if __name__ == "__main__":
    load_dotenv()

```

## File: utils\__init__.py

```python
"""
Module of code thematically unrelated to pycodetags.
"""

__all__ = ["persistent_memoize", "clear_cache", "load_dotenv"]

from pycodetags.utils.cache_utils import clear_cache, persistent_memoize
from pycodetags.utils.dotenv import load_dotenv

```

