"""
Some alternative ways to identify the current developer, which can be used to stop code if unimplemented code
is the responsibility of that developer.
"""

from __future__ import annotations

import logging
import os

# I could use git library but that also uses shell
import subprocess  # nosec
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_git_user() -> str:
    """Gets user name from local git config."""
    try:
        user = subprocess.check_output(["git", "config", "user.name"]).strip().decode("utf-8")  # nosec
        return user
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown_git_user"


def get_os_user() -> str:
    """Gets user from OS environment variables."""
    return os.getenv("USER") or os.getenv("USERNAME") or "unknown_os_user"


def get_env_user(user_env_var: str) -> str:
    """Gets user from the configured .env variable."""
    return os.getenv(user_env_var, "")


def get_current_user(method: str, user_env_var: str) -> str:
    """
    Determines the current user based on the method in the configuration.
    """
    if method == "git":
        return get_git_user()
    if method == "env":
        return get_env_user(user_env_var)
    if method == "os":
        return get_os_user()
    raise NotImplementedError("Not a known ID method")
