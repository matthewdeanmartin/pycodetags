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
from typing import Callable
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
