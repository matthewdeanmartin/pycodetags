"""Deterministic source discovery with explicit directory pruning."""

from __future__ import annotations

import os
from collections.abc import Sequence
from fnmatch import fnmatchcase
from pathlib import Path

from pycodetags.exceptions import ConfigError


def discover_files(
    root: Path, paths: Sequence[str | Path], exclude: Sequence[str] = (), python_only: bool = True
) -> list[Path]:
    """Expand paths relative to root; prune excluded directories and never follow directory symlinks.

    Patterns match root-relative POSIX paths, with fnmatch's slash-crossing '*'. A literal directory
    excludes its descendants. Missing explicit paths fail instead of silently shrinking a scan.
    """
    if isinstance(paths, (str, Path)):
        raise ConfigError("paths must be a sequence of source paths.")
    root = Path(root).resolve()
    if isinstance(exclude, str) or not all(isinstance(pattern, str) and pattern for pattern in exclude):
        raise ConfigError("exclude must be a list of nonempty path patterns.")
    found = set()
    visited = set()

    def excluded(path: Path) -> bool:
        relative = path.relative_to(root).as_posix()
        return any(
            fnmatchcase(relative, pattern.rstrip("/"))
            or fnmatchcase(relative + "/", pattern)
            or relative.startswith(pattern.rstrip("/") + "/")
            for pattern in exclude
        )

    def fail(error: OSError) -> None:
        raise error

    for supplied in paths:
        path = Path(supplied)
        path = (root / path).absolute() if not path.is_absolute() else path.absolute()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ConfigError(f"Source path is outside scan root: {path}") from error
        # Resolve '..' before applying exclusions or walking.
        path = Path(os.path.abspath(path))
        if not path.is_relative_to(root):
            raise ConfigError(f"Source path is outside scan root: {path}")
        if excluded(path):
            continue
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_symlink() or path.resolve() != path:
            continue
        if path.is_file():
            if not python_only or path.suffix == ".py":
                found.add(path)
            continue
        for folder, directories, names in os.walk(path, onerror=fail, followlinks=False):
            folder = Path(folder)
            if folder in visited:
                directories[:] = []
                continue
            visited.add(folder)
            directories[:] = sorted(
                name for name in directories if not excluded(folder / name) and not (folder / name).is_symlink()
            )
            for name in names:
                file = folder / name
                if (not python_only or file.suffix == ".py") and not excluded(file) and not file.is_symlink():
                    found.add(file)
    return sorted(found)
