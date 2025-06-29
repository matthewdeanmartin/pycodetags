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

# from pycodetags.user import get_current_user
# from pycodetags.users_from_authors import parse_authors_file_simple

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

    def __init__(self, pyproject_path: str = "pyproject.toml", set_user: str | None = None):

        self._pyproject_path = pyproject_path
        self._load()
        self.user_override = set_user

    def user_env_var(self) -> str:
        """Environment variable with active user."""
        return str(self.config.get("user_env_var", ""))

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
            raise TypeError(f"Invalid configuration: {field} must be in {accepted}")
        return str(result)

    def action_on_past_due(self) -> bool:
        """Do actions do the default action"""
        return careful_to_bool(self.config.get("action_on_past_due", False), False)

    def action_only_on_responsible_user(self) -> bool:
        """Do actions do the default action when active user matches"""
        return careful_to_bool(self.config.get("action_only_on_responsible_user", False), False)

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


if __name__ == "__main__":

    # ------------------------ USAGE EXAMPLES ------------------------

    # Lazy loading singleton config

    def example_usage() -> None:
        """Example usage of the CodeTagsConfig."""
        config = get_code_tags_config()
        if not config.runtime_behavior_enabled:
            print("Runtime behavior is disabled.")
            return

        print("Valid priorities:", config.active_schemas())

    # Setting a custom or mock config for testing or alternate use
    class MockConfig(CodeTagsConfig):
        """Mock configuration for testing purposes."""

        def __init__(self, pyproject_path: str = "pyproject.toml"):
            super().__init__(pyproject_path)
            self.config = {"valid_priorities": ["urgent"], "disable_all_runtime_behavior": False}

    # Set the mock instance
    CodeTagsConfig.set_instance(MockConfig())

    # Now using get_code_tags_config will use the mock
    example_usage()
