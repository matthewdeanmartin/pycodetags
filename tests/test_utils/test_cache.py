"""
Pytest tests for the persistent_memoize decorator.

These tests use the `tmp_path` fixture from pytest to create temporary
directories for caching, ensuring that the tests are self-contained and
do not interfere with any real cache or the filesystem.
"""

import gzip
import pickle
import time
from pathlib import Path

import pytest

# Assuming the code from the artifact is in a file named `memoizer.py`
from pycodetags.utils import clear_cache, persistent_memoize

# A global list to track call timestamps for testing purposes.
# We reset this in each test function.
call_log = []


def slow_function_factory(sleep_time: float = 0.1):
    """Factory to create a consistent slow function for testing."""

    def _slow_function(x: int, y: str = "default") -> dict:
        """A simple function that sleeps to simulate work."""
        timestamp = time.time()
        call_log.append(timestamp)
        time.sleep(sleep_time)
        return {"x": x, "y": y, "timestamp": timestamp}

    return _slow_function


def test_basic_memoization_and_cache_hit(tmp_path: Path):
    """
    Tests that a function call is cached and subsequent calls with the
    same arguments hit the cache.
    """
    global call_log
    call_log = []

    slow_function = slow_function_factory()
    memoized_func = persistent_memoize(cache_dir_override=tmp_path)(slow_function)

    # First call - should be slow and execute the function
    result1 = memoized_func(1, y="test")
    assert len(call_log) == 1

    # Second call with same args - should be fast and return cached result
    result2 = memoized_func(1, y="test")

    # Assert that the function was only actually called once
    assert len(call_log) == 1

    # Assert that the results are identical (especially the timestamp)
    assert result1 == result2

    # Assert that a cache file was created
    cache_files = list(f for f in tmp_path.iterdir() if f.name != ".gitignore")
    assert len(cache_files) == 1


def test_different_arguments_create_different_caches(tmp_path: Path):
    """
    Tests that calls with different arguments are not mixed up and
    result in separate cache entries.
    """
    global call_log
    call_log = []

    slow_function = slow_function_factory()
    memoized_func = persistent_memoize(cache_dir_override=tmp_path)(slow_function)

    # Call with first set of arguments
    result1 = memoized_func(1, y="one")
    assert len(call_log) == 1

    # Call with second set of arguments
    result2 = memoized_func(2, y="two")
    assert len(call_log) == 2

    # The results should be different
    assert result1 != result2
    assert result1["timestamp"] != result2["timestamp"]

    # There should be two separate cache files
    cache_files = list(f for f in tmp_path.iterdir() if f.name != ".gitignore")
    assert len(cache_files) == 2


def test_ttl_expires_cache(tmp_path: Path):
    """
    Tests that a cache entry is invalidated and recomputed after the
    Time-To-Live (TTL) has passed.
    """
    global call_log
    call_log = []

    slow_function = slow_function_factory()
    # Decorate with a very short TTL of 1 second
    memoized_func = persistent_memoize(ttl_seconds=1, cache_dir_override=tmp_path)(slow_function)

    # First call, populates the cache
    result1 = memoized_func(10, "ttl_test")
    assert len(call_log) == 1

    # Wait for the TTL to expire
    time.sleep(2)

    # Second call, should miss the cache and re-execute
    result2 = memoized_func(10, "ttl_test")
    assert len(call_log) == 2

    # The timestamps should be different, proving re-execution
    assert result1["timestamp"] != result2["timestamp"]


def test_clear_cache_works(tmp_path: Path):
    """
    Tests that the clear_cache function correctly removes cache files.
    """
    slow_function = slow_function_factory()
    memoized_func = persistent_memoize(cache_dir_override=tmp_path)(slow_function)

    # Create a couple of cache files
    memoized_func(1, "a")
    memoized_func(2, "b")

    cache_files_before = list(f for f in tmp_path.iterdir() if f.name != ".gitignore")
    assert len(cache_files_before) == 2

    # Clear the cache
    clear_cache(cache_dir_override=tmp_path)

    cache_files_after = list(f for f in tmp_path.iterdir() if f.name != ".gitignore")
    assert len(cache_files_after) == 0

    # Ensure .gitignore is NOT deleted
    assert (tmp_path / ".gitignore").exists()


def test_gzip_compression_works(tmp_path: Path):
    """
    Tests that enabling gzip creates a compressed cache file and that it
    can be read back correctly.
    """
    global call_log
    call_log = []

    slow_function = slow_function_factory()
    memoized_func = persistent_memoize(cache_dir_override=tmp_path, use_gzip=True)(slow_function)

    # First call, creates the gzipped cache
    result1 = memoized_func(100, "gzip")

    # Check that a .pkl.gz file was created
    cache_files = list(tmp_path.iterdir())
    assert any(f.name.endswith(".pkl.gz") for f in cache_files)

    # Second call, should read from the gzipped cache
    result2 = memoized_func(100, "gzip")

    # Function should only have been called once
    assert len(call_log) == 1
    assert result1 == result2

    # Manually verify content
    gz_file = next(f for f in tmp_path.iterdir() if f.name.endswith(".pkl.gz"))
    with gzip.open(gz_file, "rb") as f:
        data_from_file = pickle.load(f)
    assert data_from_file == result1


def test_gitignore_is_created(tmp_path: Path):
    """
    Tests that a .gitignore file is automatically created in the cache directory.
    """
    slow_function = slow_function_factory()
    memoized_func = persistent_memoize(cache_dir_override=tmp_path)(slow_function)

    # The .gitignore should exist immediately
    assert (tmp_path / ".gitignore").exists()

    # Call the function to trigger cache creation
    memoized_func(1, "init")

    # The .gitignore file should now exist
    gitignore_path = tmp_path / ".gitignore"
    assert gitignore_path.exists()

    # It should contain the correct rule
    with gitignore_path.open("r") as f:
        content = f.read()
    assert content.strip() == "*"


def test_no_pyproject_toml_raises_error(tmp_path, monkeypatch):
    """
    Tests that FileNotFoundError is raised if no pyproject.toml is found
    and no cache_dir_override is provided.
    """
    # Change the current directory to a temporary path that has no
    # pyproject.toml in its hierarchy.
    monkeypatch.chdir(tmp_path)

    # Using pytest.raises to assert that an exception is thrown
    with pytest.raises(FileNotFoundError):
        # This call should fail because it can't find the project root
        @persistent_memoize(raise_on_missing_config=True)
        def some_function(x: int) -> None:
            pass

        some_function(1)
