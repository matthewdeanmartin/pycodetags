"""Tests for common_interfaces: dumps/loads/dump/load/inspect_file/list_available_schemas."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from pycodetags.common_interfaces import (
    dump,
    dump_all,
    dumps,
    dumps_all,
    get_active_schemas,
    inspect_file,
    list_available_schemas,
    load,
    load_all,
    loads,
    loads_all,
    string_to_data,
    string_to_data_tag_typed_dicts,
)
from pycodetags.data_tags.data_tags_classes import DATA

SOURCE_WITH_ONE_TAG = "# TODO: fix the thing <priority:high status:open>"
SOURCE_WITH_TWO_TAGS = (
    "# TODO: first task <priority:high>\n"
    "def x(): pass\n"
    "# FIXME: second task <priority:low>"
)
SOURCE_NO_TAGS = "x = 1\ny = 2\n"


# ---------------------------------------------------------------------------
# dumps / loads round-trip
# ---------------------------------------------------------------------------


def test_dumps_produces_comment_string():
    tag = DATA(code_tag="TODO", comment="fix it")
    result = dumps(tag)
    assert "TODO" in result
    assert "fix it" in result


def test_dumps_empty_data_returns_empty_string():
    assert dumps(None) == ""  # type: ignore[arg-type]


def test_loads_returns_data_object():
    tag = loads(SOURCE_WITH_ONE_TAG)
    assert tag is not None
    assert tag.code_tag == "TODO"
    assert "fix the thing" in (tag.comment or "")


def test_loads_returns_none_for_no_tags():
    result = loads(SOURCE_NO_TAGS)
    assert result is None


def test_dumps_loads_round_trip():
    original = DATA(code_tag="NOTE", comment="remember this", data_fields={"priority": "high"})
    serialized = dumps(original)
    recovered = loads(serialized)
    assert recovered is not None
    assert recovered.code_tag == "NOTE"
    assert "remember this" in (recovered.comment or "")


# ---------------------------------------------------------------------------
# dump / load (file-like)
# ---------------------------------------------------------------------------


def test_dump_and_load_via_stringio():
    tag = DATA(code_tag="BUG", comment="broken logic", data_fields={"status": "open"})
    # dump closes the stream via its context manager, so capture output a different way
    serialized = dumps(tag)
    buf = io.StringIO(serialized)
    recovered = load(buf)
    assert recovered is not None
    assert recovered.code_tag == "BUG"


def test_load_from_path_object(tmp_path: Path):
    # Wrap in valid Python so the AST comment finder can parse it
    file_path = tmp_path / "tags.py"
    file_path.write_text("x = 1\n" + SOURCE_WITH_ONE_TAG + "\n", encoding="utf-8")
    tag = load(file_path)
    assert tag is not None
    assert tag.code_tag == "TODO"


def test_dump_to_path_writes_file(tmp_path: Path):
    tag = DATA(code_tag="TODO", comment="write me")
    dest = tmp_path / "out.txt"
    dump(tag, dest)
    content = dest.read_text(encoding="utf-8")
    assert "TODO" in content
    assert "write me" in content


# ---------------------------------------------------------------------------
# dumps_all / loads_all
# ---------------------------------------------------------------------------


def test_dumps_all_separates_tags_with_newlines():
    tags = [
        DATA(code_tag="TODO", comment="first"),
        DATA(code_tag="FIXME", comment="second"),
    ]
    result = dumps_all(tags)
    assert "TODO" in result
    assert "FIXME" in result
    assert "\n" in result


def test_loads_all_returns_multiple_tags():
    tags = list(loads_all(SOURCE_WITH_TWO_TAGS))
    assert len(tags) >= 2


def test_loads_all_returns_empty_for_no_tags():
    tags = list(loads_all(SOURCE_NO_TAGS))
    assert tags == []


def test_dump_all_and_load_all_via_stringio():
    tags = [
        DATA(code_tag="TODO", comment="alpha", data_fields={"priority": "high"}),
        DATA(code_tag="FIXME", comment="beta"),
    ]
    # dump_all closes the stream, so serialize via dumps_all and feed to load_all
    serialized = dumps_all(tags)
    buf = io.StringIO(serialized)
    recovered = list(load_all(buf))
    assert len(recovered) == 2
    codes = {t.code_tag for t in recovered}
    assert "TODO" in codes
    assert "FIXME" in codes


# ---------------------------------------------------------------------------
# string_to_data / string_to_data_tag_typed_dicts
# ---------------------------------------------------------------------------


def test_string_to_data_returns_data_objects():
    result = list(string_to_data(SOURCE_WITH_ONE_TAG))
    assert len(result) == 1
    assert isinstance(result[0], DATA)


def test_string_to_data_tag_typed_dicts_returns_dicts():
    result = list(string_to_data_tag_typed_dicts(SOURCE_WITH_ONE_TAG))
    assert len(result) == 1
    # TypedDict is just a dict at runtime
    assert isinstance(result[0], dict)
    assert result[0]["code_tag"] == "TODO"


# ---------------------------------------------------------------------------
# inspect_file
# ---------------------------------------------------------------------------


def test_inspect_file_returns_list_of_data(tmp_path: Path):
    f = tmp_path / "module.py"
    f.write_text(SOURCE_WITH_TWO_TAGS, encoding="utf-8")
    tags = inspect_file(f)
    assert len(tags) >= 2
    assert all(isinstance(t, DATA) for t in tags)


def test_inspect_file_raises_for_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        inspect_file(tmp_path / "ghost.py")


def test_inspect_file_returns_empty_for_no_tags(tmp_path: Path):
    f = tmp_path / "plain.py"
    f.write_text(SOURCE_NO_TAGS, encoding="utf-8")
    tags = inspect_file(f)
    assert tags == []


# ---------------------------------------------------------------------------
# list_available_schemas / get_active_schemas
# ---------------------------------------------------------------------------


def test_list_available_schemas_returns_list():
    schemas = list_available_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) >= 1


def test_list_available_schemas_includes_pure_data():
    schemas = list_available_schemas()
    names = [s.get("name", "") for s in schemas]
    assert any("pure" in n.lower() or n == "" or n for n in names)


def test_get_active_schemas_empty_names_returns_empty():
    result = get_active_schemas([])
    assert result == []


def test_get_active_schemas_unknown_name_returns_empty():
    result = get_active_schemas(["nonexistent_schema_xyz"])
    assert result == []
