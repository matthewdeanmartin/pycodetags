"""Reproducible core benchmark; run with python -m tests.benchmark_core --output PATH."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import tempfile
from dataclasses import asdict, replace
from pathlib import Path
from time import perf_counter

from pycodetags import TagIndex, inspect_file, update_tags
from pycodetags.discovery import discover_files
from pycodetags.python.comment_finder import scan_comment_blocks


def timed(action, repetitions=3):
    durations = []
    for _ in range(repetitions):
        started = perf_counter()
        action()
        durations.append(perf_counter() - started)
    return statistics.median(durations)


def benchmark(root, file_count, tags_per_file):
    root.mkdir()
    source = root / "src"
    source.mkdir()
    (root / "pyproject.toml").write_text('[tool.pycodetags]\nschema="TDG"\nsrc=["src"]\n', encoding="utf-8")
    for number in range(file_count):
        text = (
            "\n".join(
                f"# TODO: task {number * tags_per_file + tag}\n# id={number * tags_per_file + tag} issue=100\n# Description of the task.\nvalue = 1"
                for tag in range(tags_per_file)
            )
            + "\n"
        )
        (source / f"file{number:04}.py").write_bytes(text.encode())
    files = discover_files(root, ["src"])

    def fresh_scan():
        return [tag for path in discover_files(root, ["src"]) for tag in inspect_file(path, schema="TDG")]

    def cold_scan():
        scan_comment_blocks.cache_clear()
        return fresh_scan()

    discovery = timed(lambda: discover_files(root, ["src"]))
    cold = timed(cold_scan)
    warm = timed(fresh_scan)
    scan_comment_blocks.cache_clear()
    index = TagIndex(root)
    initial = index.refresh()
    assert len(index.query_snapshot()) == file_count * tags_per_file
    assert [tag.to_flat_dict() for tag in index.query_snapshot()] == [tag.to_flat_dict() for tag in fresh_scan()]
    refreshes = [index.refresh() for _ in range(3)]
    lookup = timed(lambda: index.query_snapshot(tag_id="0"), repetitions=200)
    tracker_lookup = timed(
        lambda: index.query_snapshot(tracker="https://github.com/example/project/issues/1"), repetitions=200
    )
    file_lookup = timed(lambda: index.query_snapshot(file_path=files[0]), repetitions=30)
    first = files[0]
    original = first.read_bytes()
    changes = []
    for number in range(3):
        first.write_bytes(original.replace(b"task 0", f"edited {number}".encode(), 1))
        changes.append(index.refresh())
    batch_durations = []
    for _ in range(3):
        first.write_bytes(original)
        tags = inspect_file(first, schema="TDG")[:100]
        started = perf_counter()
        update_tags(first, [(tag, replace(tag, title=tag.title + " updated")) for tag in tags])
        batch_durations.append(perf_counter() - started)
    return {
        "files": file_count,
        "tags": file_count * tags_per_file,
        "source_bytes": initial.bytes_read,
        "index_bytes": index.database_path.stat().st_size,
        "discovery_seconds": discovery,
        "uncached_scan_seconds": cold,
        "warm_scan_seconds": warm,
        "initial_refresh": asdict(initial),
        "warm_refresh": {key: statistics.median(asdict(item)[key] for item in refreshes) for key in asdict(initial)},
        "one_file_change": {key: statistics.median(asdict(item)[key] for item in changes) for key in asdict(initial)},
        "id_lookup_seconds": lookup,
        "tracker_miss_seconds": tracker_lookup,
        "file_lookup_seconds": file_lookup,
        "batch_update_tags": min(100, tags_per_file),
        "batch_update_seconds": statistics.median(batch_durations),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pycodetags-benchmark-") as folder:
        root = Path(folder)
        results = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "repetitions": 3,
            "many_small_files": benchmark(root / "small", 300, 10),
            "few_large_files": benchmark(root / "large", 3, 1000),
        }
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
