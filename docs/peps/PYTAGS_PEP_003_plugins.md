# PYCODETAGS PEP 003 — Performance and Caching

| PEP:             | 003                                                                               |
|------------------|-----------------------------------------------------------------------------------|
| Title:           | Performance and Caching                                                           |
| Author:          | Matthew Martin [matthewdeanmartin@gmail.com](mailto\:matthewdeanmartin@gmail.com) |
| Author:          | ChatGPT (gpt-4-turbo, OpenAI)                                                     |
| Status:          | Draft                                                                             |
| Type:            | Standards Track                                                                   |
| Created:         | 2025-07-12                                                                        |
| License:         | MIT                                                                               |
| Intended Version | ≥ 0.7.0                                                                           |

## Abstract

This PEP outlines strategies and implementation details for improving the performance of PyCodeTags via persistent
caching, organized storage, and systematic benchmarking, while remaining entirely within the standard Python ecosystem.

---

## Motivation

PyCodeTags performs source inspection, comment parsing, plugin hook execution, and JMESPath evaluation. While powerful,
these operations incur performance costs on large repositories. This PEP addresses:

* Long-running scans for large codebases.
* Inefficient cache invalidation.
* Lack of app version-aware cache separation.
* Need for consistent benchmarking across changes.

---

## Goals

1. **Improve cache lookup and eviction performance**.
2. **Enable cache invalidation upon app version changes**.
3. **Provide consistent, repeatable performance benchmarks**.
4. **Avoid third-party dependencies (pure Python only)**.

---

## Proposal: Caching Enhancements

### 1. Directory Layout for Caching

Cached files will be written to:

```
.pycodetags_cache/{version}/YYYY/MM/DD/hash.pkl(.gz)
```

* **`{version}`**: From `pycodetags.__version__`
* **`YYYY/MM/DD`**: UTC-based date hierarchy
* **`hash.pkl(.gz)`**: Based on the SHA256 of the function name and arguments

This layout supports:

* Efficient eviction (delete stale days/months/version en masse)
* Simpler debugging (e.g., inspecting today's cache entries)
* Concurrent cache usage across multiple app versions

### 2. Version-Aware Cache Namespacing

The outermost folder (`{version}`) ensures that each PyCodeTags release maintains isolated caches. When a new version is
installed, old caches will not be reused — avoiding subtle bugs from schema or parser changes.

On startup, PyCodeTags will optionally clean up non-matching version directories if desired (`--clean-old-caches`).

### 3. Staleness and TTL Control

Cached files will store:

* Their timestamp (via `mtime`)
* Optional metadata (via a side `.meta` file, optional)
* TTL will default to **7 days** (configurable)

Automatic cleanup will:

* Prune files older than the TTL
* Optionally remove entire YYYY/MM subfolders if fully stale

### 4. Compatibility with `persistent_memoize`

The current `persistent_memoize` decorator will be extended to:

* Detect the app version from `pycodetags.__version__`
* Compute folder layout automatically
* Create the directory tree lazily
* Provide explicit `evict_old_caches()` and `evict_all_caches()` utilities

```python
@persistent_memoize(ttl_seconds=86400 * 7, organize_by_date=True, include_version=True)
def find_comment_blocks_from_string(...):
    ...
```

---

## Proposal: Benchmarking

### 1. Baseline Suite

A minimal benchmark suite will be added under `tests/performance/`:

| Benchmark                 | Description                                                   |
|---------------------------|---------------------------------------------------------------|
| `bench_collect_stdlib.py` | Measures time to collect data from a large module like `http` |
| `bench_inspect_repo.py`   | Measures full scan time on a mid-size repo                    |
| `bench_comment_finder.py` | Measures speed of comment extraction from large files         |
| `bench_parse_codetags.py` | Measures tag parsing performance over 1000 synthetic blocks   |

### 2. Benchmarking Harness

A CLI tool:

```bash
python -m pycodetags.benchmarks --baseline
```

Will:

* Run all benchmarks
* Save output to `benchmark_results.json`
* Compare to previous runs

### 3. Pure Python Tools Only

To avoid adding dependencies:

* Use `time.perf_counter()` for timing
* Optionally use `pstats` for profiling
* Use standard `unittest` or `doctest`-like structures

### 4. Performance Targets

Each benchmark will define:

* A historical average
* A “slowdown threshold” (e.g., 20%)
* Fail CI if regression exceeds threshold (optional via env var)

---

## Configuration Options

Users may configure caching behavior via `pyproject.toml`:

```toml
[tool.pycodetags.cache]
ttl_days = 7
enable_version_namespacing = true
enable_date_subfolders = true
clean_old_versions = true
```

---

## Backwards Compatibility

No breaking changes are introduced:

* `persistent_memoize` continues to work as before
* Existing caches remain readable (flat layout will still be supported if config disables structured layout)

---

## Implementation Plan

* [x] Update `persistent_memoize` to support versioned/date-based cache layout
* [ ] Add cleanup utilities (`clear_cache`, `clear_old_versions`)
* [ ] Add benchmark suite under `tests/performance/`
* [ ] Document config options
* [ ] Add support to invalidate stale schemas/plugins via hash (future work)

---

## Rejected Ideas

* Using external cache libraries (e.g., `joblib`, `diskcache`) — violates pure Python constraint.
* SQLite cache — would add complexity and I/O overhead.

---

## References

* [PEP 350](https://peps.python.org/pep-0350/) – Code Tags for Python
* [Jupyter’s caching techniques](https://github.com/ipython/ipython/issues/10092)
* Internal memoization decorators in `functools` and `lru_cache`

## Copyright

This document is licensed under the MIT License.
