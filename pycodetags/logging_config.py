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
