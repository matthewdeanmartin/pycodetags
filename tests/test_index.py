"""Source-authoritative index behavior, invalidation, and query plans."""

import os
import sqlite3
from contextlib import closing
from dataclasses import replace

import pytest

from pycodetags import TagIndex, inspect_file, update_tags
from pycodetags.app_config.config import CodeTagsConfig
from pycodetags.discovery import discover_files
from pycodetags.exceptions import ConfigError, DataTagError, DataTagParseError, FileParsingError
from pycodetags.index import IndexStateError


def project(tmp_path, schema="TDG"):
    (tmp_path / "pyproject.toml").write_text(f'[tool.pycodetags]\nschema="{schema}"\nsrc=["src"]\n', encoding="utf-8")
    folder = tmp_path / "src"
    folder.mkdir()
    path = folder / "a.py"
    text = (
        "# TODO: first\n# id=1 issue=100 tracker=https://github.com/a/b/issues/2\n# body\n"
        if schema == "TDG"
        else "# TODO: first\n# body\n# <id=1 issue=100 tracker=https://github.com/a/b/issues/2>\n"
    )
    path.write_bytes(text.encode())
    return TagIndex(tmp_path), path


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_fresh_snapshot_equals_parser_and_queries_use_indexes(tmp_path, schema):
    index, path = project(tmp_path, schema)
    result = index.refresh()
    assert (result.files, result.parsed, result.tags) == (1, 1, 1)
    assert index.query_snapshot() == inspect_file(path, schema=schema)
    assert index.query_snapshot(tag_id="1") == index.query_snapshot(file_path="src/a.py")
    assert index.query_snapshot(tracker="https://github.com/a/b/issues/2") == index.query_snapshot()
    assert index.query_snapshot(tag_id="100") == []  # Parent issue is not tag identity.
    assert index.query_snapshot(tag_id="1", tracker="missing") == []
    with closing(sqlite3.connect(index.database_path)) as connection:
        for column in ("tag_id", "tracker", "file_path"):
            plan = connection.execute(
                f"EXPLAIN QUERY PLAN SELECT payload FROM tags WHERE {column}=?", ("1",)
            ).fetchall()
            assert any("SEARCH" in row[3] and "INDEX" in row[3] for row in plan)


def test_unchanged_refresh_never_calls_parser(tmp_path, monkeypatch):
    index, path = project(tmp_path)
    index.refresh()

    def unexpected(*args, **kwargs):
        raise AssertionError("Unchanged file should not be parsed")

    monkeypatch.setattr("pycodetags.index.string_to_data", unexpected)
    result = index.refresh()
    assert (result.parsed, result.unchanged, result.bytes_read) == (0, 1, path.stat().st_size)


def test_same_size_and_timestamp_edit_is_detected_and_snapshot_is_explicit(tmp_path):
    index, path = project(tmp_path)
    index.refresh()
    old = index.query_snapshot()[0]
    times = path.stat()
    path.write_bytes(path.read_bytes().replace(b"first", b"other"))
    os.utime(path, ns=(times.st_atime_ns, times.st_mtime_ns))
    assert index.query_snapshot()[0].title == "first"
    with pytest.raises(DataTagError, match="Tag mismatch"):
        update_tags(path, [(old, replace(old, title="unsafe"))])
    assert index.refresh().parsed == 1
    assert index.query_snapshot()[0].title == "other"


def test_indexed_record_can_be_mutated_then_refreshed(tmp_path):
    index, path = project(tmp_path)
    index.refresh()
    old = index.query_snapshot(tag_id="1")[0]
    update_tags(path, [(old, replace(old, title="new"))])
    index.refresh()
    assert index.query_snapshot()[0].title == "new"


def test_deleted_and_excluded_files_are_removed_without_stale_rows(tmp_path):
    index, path = project(tmp_path)
    second = path.with_name("b.py")
    second.write_bytes(b"# TODO: second\n")
    index.refresh()
    path.unlink()
    result = index.refresh(exclude=["src/b.py"])
    assert (result.removed, result.files, result.tags) == (2, 0, 0)
    assert index.query_snapshot() == []


def test_schema_config_and_parser_versions_trigger_reparse(tmp_path, monkeypatch):
    index, path = project(tmp_path)
    index.refresh()
    config = tmp_path / "pyproject.toml"
    config.write_text('[tool.pycodetags]\nschema="PEP350"\nsrc=["src"]\n', encoding="utf-8")
    assert index.refresh().parsed == 1
    assert index.query_snapshot() == []
    monkeypatch.setattr("pycodetags.index.PARSER_VERSION", 99)
    assert index.refresh().parsed == 1


def test_path_rules_and_exclusions_reload_from_config(tmp_path):
    index, path = project(tmp_path)
    path.write_bytes(b"# TODO: first <>\n")
    config = tmp_path / "pyproject.toml"
    config.write_text(
        '[tool.pycodetags]\nsrc=["src"]\n[[tool.pycodetags.schema_paths]]\npath="src/*.py"\nschema="PEP350"\n',
        encoding="utf-8",
    )
    index.refresh()
    assert index.query_snapshot()[0].title == "first"
    config.write_text('[tool.pycodetags]\nschema="TDG"\nsrc=["src"]\nexclude=["src"]\n', encoding="utf-8")
    assert index.refresh().removed == 1


@pytest.mark.parametrize("bad", [b'# TODO: bad\n# id="unterminated\n', b'"""unterminated'])
def test_failed_refresh_rolls_back_all_files(tmp_path, bad):
    index, path = project(tmp_path)
    index.refresh()
    path.write_bytes(path.read_bytes().replace(b"first", b"other"))
    path.with_name("z.py").write_bytes(bad)
    with pytest.raises((DataTagParseError, FileParsingError)):
        index.refresh()
    assert index.query_snapshot()[0].title == "first"


def test_index_deletion_is_recoverable(tmp_path):
    index, path = project(tmp_path)
    index.refresh()
    expected = index.query_snapshot()
    index.database_path.unlink()
    with pytest.raises(IndexStateError, match="missing"):
        index.query_snapshot()
    assert index.refresh().parsed == 1
    assert index.query_snapshot() == expected
    assert path.exists()


def test_foreign_or_corrupt_database_is_not_overwritten(tmp_path):
    index, path = project(tmp_path)
    with closing(sqlite3.connect(index.database_path)) as connection:
        connection.execute("CREATE TABLE precious (value TEXT)")
    before = index.database_path.read_bytes()
    with pytest.raises(IndexStateError):
        index.refresh()
    assert index.database_path.read_bytes() == before
    index.database_path.write_bytes(b"corrupt cache")
    with pytest.raises(IndexStateError):
        index.refresh()
    assert index.database_path.read_bytes() == b"corrupt cache"


def test_missing_schema_and_overlapping_rules_fail(tmp_path):
    folder = tmp_path / "src"
    folder.mkdir()
    (folder / "a.py").write_bytes(b"# TODO: a\n")
    with pytest.raises(ConfigError):
        TagIndex(tmp_path).refresh(paths=["src"])
    config = tmp_path / "pyproject.toml"
    config.write_text(
        '[tool.pycodetags]\nsrc=["src"]\n[[tool.pycodetags.schema_paths]]\npath="src/*"\nschema="TDG"\n[[tool.pycodetags.schema_paths]]\npath="*"\nschema="TDG"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="Overlapping"):
        TagIndex(tmp_path).refresh()


def test_discovery_prunes_directories_and_deduplicates_paths(tmp_path, monkeypatch):
    index, path = project(tmp_path)
    vendor = path.parent / "vendor"
    vendor.mkdir()
    (vendor / "bad.py").write_bytes(b"invalid")
    real_walk = os.walk
    visited = []

    def walk(*args, **kwargs):
        for item in real_walk(*args, **kwargs):
            visited.append(item[0])
            yield item

    monkeypatch.setattr("pycodetags.discovery.os.walk", walk)
    files = discover_files(tmp_path, ["src", path, "src"], ["src/vendor/**"])
    assert files == [path]
    assert vendor not in visited
    assert index.refresh(paths=["src", "src"], exclude=["src/vendor"]).files == 1


def test_duplicate_ids_return_all_matches(tmp_path):
    index, path = project(tmp_path)
    path.with_name("b.py").write_bytes(path.read_bytes())
    index.refresh()
    assert len(index.query_snapshot(tag_id="1")) == 2


def test_exclusions_apply_to_id_assignment(tmp_path):
    from pycodetags.id_command import run

    index, path = project(tmp_path)
    ignored = path.with_name("ignored.py")
    original = b"# TODO: ignored\n"
    ignored.write_bytes(original)
    run(
        [str(path.parent)], schema="TDG", counter_root=tmp_path, exclude=["src/ignored.py"], writer=lambda message: None
    )
    assert ignored.read_bytes() == original


def test_exclusions_apply_to_aggregate(tmp_path):
    from pycodetags.aggregate import aggregate_all_kinds_multiple_input

    index, path = project(tmp_path)
    path.with_name("ignored.py").write_bytes(b"# TODO: ignored\n")
    CodeTagsConfig.set_instance(CodeTagsConfig(str(tmp_path / "pyproject.toml")))
    tags = aggregate_all_kinds_multiple_input([], [str(path.parent)], schema="TDG", exclude=["src/ignored.py"])
    assert [tag.title for tag in tags] == ["first"]


def test_custom_schema_changes_invalidate_existing_files(tmp_path):
    from pycodetags import TDGSchema

    index, path = project(tmp_path)
    index.schema = dict(TDGSchema)
    index.refresh()
    index.schema = dict(TDGSchema, matching_tags=["BUG"])
    assert index.refresh().parsed == 1
    assert index.query_snapshot() == []


def test_schema_version_mismatch_requires_rebuild(tmp_path):
    index, path = project(tmp_path)
    index.refresh()
    with closing(sqlite3.connect(index.database_path)) as connection:
        connection.execute("PRAGMA user_version=999")
    with pytest.raises(IndexStateError, match="Incompatible"):
        index.query_snapshot()
    with pytest.raises(IndexStateError, match="Incompatible"):
        index.refresh()


def test_missing_explicit_source_does_not_erase_snapshot(tmp_path):
    index, path = project(tmp_path)
    index.refresh()
    with pytest.raises(FileNotFoundError):
        index.refresh(paths=["missing"])
    assert len(index.query_snapshot()) == 1


def test_empty_directory_still_requires_explicit_schema(tmp_path):
    (tmp_path / "src").mkdir()
    with pytest.raises(ConfigError):
        TagIndex(tmp_path).refresh(paths=["src"])


def test_discovery_rejects_path_escape_and_invalid_options(tmp_path):
    with pytest.raises(ConfigError, match="outside"):
        discover_files(tmp_path, ["../"])
    with pytest.raises(ConfigError):
        discover_files(tmp_path, [], exclude="vendor")
    with pytest.raises(ConfigError):
        TagIndex(tmp_path).refresh(paths="src")


def test_overlapping_aggregate_inputs_only_parse_each_file_once(tmp_path, monkeypatch):
    import pycodetags.aggregate as aggregate

    index, path = project(tmp_path)
    calls = []
    actual = aggregate.iterate_comments_from_file

    def counted(file, *args, **kwargs):
        calls.append(file)
        return actual(file, *args, **kwargs)

    monkeypatch.setattr(aggregate, "iterate_comments_from_file", counted)
    tags = aggregate.aggregate_all_kinds_multiple_input([], [str(path.parent), str(path)], schema="TDG")
    assert len(tags) == 1
    assert calls == [str(path)]
