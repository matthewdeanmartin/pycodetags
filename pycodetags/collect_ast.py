"""
Collection methods that rely on AST parsing

TODO: https://pypi.org/project/ast-comments/
"""

from __future__ import annotations

import ast
import logging
from types import ModuleType
from typing import Any, cast

from pycodetags.todo_tag_types import TodoException

logger = logging.getLogger(__name__)


class TodoExceptionCollector:
    """Collector for TodoExceptions that are raised during code execution."""

    def __init__(self) -> None:
        self.exceptions: list[TodoException] = []

    def collect_from_source_analysis(self, module: ModuleType) -> list[TodoException]:
        """
        Analyze source code to find TodoException raises.

        This method parses the source code to find TodoException raises
        without actually executing the code.
        """
        exceptions: list[TodoException] = []

        if not hasattr(module, "__file__") or module.__file__ is None:
            return exceptions

        try:
            with open(module.__file__, encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Raise) and node.exc:
                    if (
                        isinstance(node.exc, ast.Call)
                        and isinstance(node.exc.func, ast.Name)
                        and node.exc.func.id == "TodoException"
                    ):

                        # Extract arguments from the TodoException call
                        exception_data = self._extract_exception_args(node.exc)
                        if exception_data:
                            exceptions.append(TodoException(**exception_data))

        except (FileNotFoundError, SyntaxError, UnicodeDecodeError):
            pass

        return exceptions

    def _extract_exception_args(self, call_node: ast.Call) -> dict[str, Any]:
        """Extract arguments from a TodoException call node.

        Args:
            call_node: The AST Call node representing the TodoException call

        Returns:
            dict: Dictionary of extracted arguments
        """
        args = {}

        # Handle keyword arguments
        for keyword in call_node.keywords:
            if keyword.arg in ["assignee", "due_date", "message"]:
                if isinstance(keyword.value, ast.Constant):
                    args[keyword.arg] = keyword.value.value
                elif isinstance(keyword.value, ast.Str):  # Python < 3.8 compatibility
                    args[cast(Any, keyword.value)] = keyword.value.s

        return args if args else {}
