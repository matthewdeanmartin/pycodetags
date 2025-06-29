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
        self.todos: list[DATA] = []
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
        self._reset()
        self._collect_recursive(module, include_submodules, max_depth, 0)
        return self.todos.copy()

    def _reset(self) -> None:
        """Reset internal collections."""
        self.todos.clear()
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
            self._check_object_for_todos(obj)
            # Classes are showing up as functions?! Yes.
            self._collect_from_class_attributes(obj, include_submodules, max_depth, current_depth)
        if isinstance(obj, (list, set, tuple)) and obj:
            logger.debug(f"Found a list/set/tuple {obj}")
            for item in obj:
                self._check_object_for_todos(item)
        else:
            # self._collect_from_class_attributes(obj, include_submodules, max_depth, current_depth)
            logger.debug(f"Don't know what to do with {obj}")

    def _check_object_for_todos(self, obj: Any) -> None:
        """Check if an object has TODO/Done metadata."""
        if hasattr(obj, "todo_meta"):
            if isinstance(obj.todo_meta, DATA):
                logger.info(f"Found todo, by instance and has todo_meta attr on {obj}")
                self.todos.append(obj.todo_meta)

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
