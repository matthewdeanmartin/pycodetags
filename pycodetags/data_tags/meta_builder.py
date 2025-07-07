"""
Universal Meta. This needs to eventually hook into plugin system so plugins can specify their own meta.
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import toml as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[no-redef,assignment]

# from pycodetags_issue_tracker.issue_tracker_config import get_issue_tracker_config
__all__ = ["build_meta_object"]


def get_project_version_from_toml(pyproject_path: str = "pyproject.toml") -> str:
    """
    Reads the project version from a pyproject.toml file.

    It checks for the version in common locations used by packaging tools
    like Poetry and standard PEP 621.

    Args:
        pyproject_path: The path to the pyproject.toml file.

    Returns:
        The project version string, or "0.0.0" if not found.
    """
    if tomllib is None or not os.path.exists(pyproject_path):
        return "0.0.0"

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Check for PEP 621 `[project]` table
        if "project" in data and "version" in data["project"]:
            return data["project"]["version"]

        # Check for `[tool.poetry]` table
        if "tool" in data and "poetry" in data["tool"] and "version" in data["tool"]["poetry"]:
            return data["tool"]["poetry"]["version"]

    except Exception:
        # Gracefully handle parsing errors or missing keys
        return "0.0.0"

    return "0.0.0"


def build_meta_object(module_or_file_name: str | None = None, pyproject_path: str = "pyproject.toml") -> dict[str, Any]:
    """
    Builds the 'meta' object containing contextual information for
    use in JMESPath expression evaluation within field_infos.

    This object can be extended with more project-specific or
    environment-specific data as needed.

    Args:
        module_or_file_name: The name of the module (e.g., 'a.b.c') or file path
                             (e.g., 'path/to/file.py') being processed.
        pyproject_path: Path to pyproject.toml

    Returns:
        A dictionary containing metadata.
    """
    # config = get_issue_tracker_config()

    # TODO: Stomp out time zones.
    now = datetime.datetime.now()

    simple_module_name = "unknown_module"
    if module_or_file_name:
        # If the input is a python file, get the name without the extension.
        if module_or_file_name.endswith(".py"):
            simple_module_name = Path(module_or_file_name).stem
        # Otherwise, assume it's a qualified module name and get the last part.
        else:
            simple_module_name = module_or_file_name.split(".")[-1]

    project_version = get_project_version_from_toml(pyproject_path)

    meta = {
        # TODO: move to issue tracker plugin
        # "user": {
        #     "name": config.current_user(),
        # },
        "timestamp": {
            "date": now.strftime("%Y-%m-%d"),
            "datetime": now.isoformat(),
        },
        "project": {
            "version": project_version,
        },
        "module": simple_module_name,
        # TODO: move to issue tracker plugin
        # This map is used by the 'priority' field's JMESPath expression
        # to set a default priority based on the code tag type.
        "priority_map": {
            "BUG": "high",
            "FIXME": "high",
            "ALERT": "critical",
            "TODO": "medium",
            "REQUIREMENT": "medium",
            "STORY": "medium",
            "IDEA": "low",
            "HACK": "low",
            "PORT": "medium",
            "DOCUMENT": "low",
        },
    }
    return meta
