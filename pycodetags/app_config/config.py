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
import sys
from fnmatch import fnmatchcase
from pathlib import Path
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
    instance: CodeTagsConfig | None = None
    config: dict[str, Any] = {}

    def __init__(self, pyproject_path: str = "pyproject.toml"):

        self.pyproject_path = Path(pyproject_path).resolve()
        self.load_config()

    def load_config(self) -> None:
        if not self.pyproject_path.exists():
            self.config = {}
            return

        try:
            with open(
                self.pyproject_path,
                "rb" if "tomllib" in sys.modules else "r",
                **({} if "tomllib" in sys.modules else {"encoding": "utf-8"}),
            ) as stream:
                data = tomllib.load(stream) if "tomllib" in sys.modules else toml.load(stream)
        except (ValueError, UnicodeError) as error:
            raise ConfigError(f"Invalid TOML configuration in {self.pyproject_path}: {error}") from error
        tool = data.get("tool", {})
        self.config = tool.get("pycodetags", {}) if isinstance(tool, dict) else None
        if not isinstance(self.config, dict):
            raise ConfigError("[tool.pycodetags] must be a TOML table.")
        for key in ("src", "modules", "exclude"):
            values = self.config.get(key, [])
            if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
                raise ConfigError(f"{key} must be a list of nonempty strings.")

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
        return [str(path) for path in self.config.get("src", [])]

    def schema_for_path(self, file_path: str | Path | None = None) -> str:
        """Select a configured schema. A matching path rule overrides the explicit project selection."""
        rules = self.config.get("schema_paths", [])
        if not isinstance(rules, list):
            raise ConfigError("schema_paths must be a list of {path, schema} tables.")
        matches = []
        relative = None
        if file_path is not None:
            try:
                relative = Path(file_path).resolve().relative_to(self.pyproject_path.parent).as_posix()
            except ValueError:
                pass
        for rule in rules:
            if (
                not isinstance(rule, dict)
                or not isinstance(rule.get("path"), str)
                or not isinstance(rule.get("schema"), str)
            ):
                raise ConfigError("Each schema_paths entry requires string path and schema values.")
            if relative is not None and fnmatchcase(relative, rule["path"]):
                matches.append(rule["schema"])
        if len(matches) > 1:
            raise ConfigError(f"Overlapping schema_paths rules for {file_path}; make the rules disjoint.")
        selection = matches[0] if matches else self.config.get("schema")
        if not isinstance(selection, str) or not selection.strip():
            raise ConfigError(
                "Select a schema explicitly: set [tool.pycodetags] schema = 'TDG' or 'PEP350', or pass schema=."
            )
        return selection

    def active_schemas(self) -> list[str]:
        """Schemas to detect in source comments."""
        return [str(_).lower() for _ in self.config.get("active_schemas", [])]

    @classmethod
    def get_instance(cls, pyproject_path: str = "pyproject.toml") -> CodeTagsConfig:
        """Get the singleton instance of CodeTagsConfig."""
        if cls.instance is None:
            cls.instance = cls(pyproject_path)
        return cls.instance

    @classmethod
    def set_instance(cls, instance: CodeTagsConfig | None) -> None:
        """Set a custom instance of CodeTagsConfig."""
        cls.instance = instance


def get_code_tags_config() -> CodeTagsConfig:
    return CodeTagsConfig.get_instance()
