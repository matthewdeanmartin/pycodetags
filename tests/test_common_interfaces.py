"""Public I/O retains explicit schema provenance and never closes caller streams."""

import io
from dataclasses import replace

import pytest

from pycodetags import DATA, dump, dump_all, dumps, dumps_all, list_available_schemas, load, load_all, loads, loads_all
from pycodetags.app_config import CodeTagsConfig
from pycodetags.exceptions import ConfigError, SchemaError


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_public_single_record_io(schema, tmp_path):
    tag = DATA(code_tag="TODO", title="title", body="body", tag_id="17")
    text = dumps(tag, schema=schema)
    stream = io.StringIO()
    dump(tag, stream, schema=schema)
    assert not stream.closed
    assert stream.getvalue() == text
    stream.seek(0)
    recovered = load(stream, schema=schema)
    assert not stream.closed
    assert (recovered.title, recovered.body, recovered.tag_id) == ("title", "body", "17")
    path = tmp_path / "tag.py"
    dump(tag, path, schema=schema)
    assert load(path, schema=schema).body == "body"


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_public_many_record_io(schema, tmp_path):
    tags = [DATA(code_tag="TODO", title="first"), DATA(code_tag="FIXME", title="second", body="line\n\nline")]
    text = dumps_all(tags, schema=schema)
    assert len(loads_all(text, schema=schema)) == 2
    stream = io.StringIO()
    dump_all(iter(tags), stream, schema=schema)
    stream.seek(0)
    recovered = load_all(stream, schema=schema)
    assert not stream.closed
    assert [tag.title for tag in recovered] == ["first", "second"]
    assert recovered[1].body == "line\n\nline"
    path = tmp_path / "tags.py"
    dump_all(tags, path, schema=schema)
    assert len(load_all(path, schema=schema)) == 2


def test_record_keeps_explicit_schema_after_project_changes(tmp_path, monkeypatch):
    tag = loads("# TODO: title\n# body", schema="TDG")
    monkeypatch.chdir(tmp_path)
    CodeTagsConfig.set_instance(None)
    assert dumps(tag) == "# TODO: title\n# body"
    assert tag.as_data_comment() == dumps(tag)
    assert dumps(tag, schema="PEP350").endswith("<>")


def test_unconfigured_dump_does_not_truncate_destination(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "output.py"
    path.write_text("valuable content", encoding="utf-8")
    with pytest.raises(ConfigError):
        dump(DATA(code_tag="TODO", title="title"), path)
    assert path.read_text(encoding="utf-8") == "valuable content"


def test_invalid_later_record_does_not_partially_write(tmp_path):
    path = tmp_path / "output.py"
    path.write_text("valuable content", encoding="utf-8")
    tags = [DATA(code_tag="TODO", title="ok"), DATA(code_tag="UNRECOGNIZED", title="bad")]
    with pytest.raises(SchemaError):
        dump_all(tags, path, schema="TDG")
    assert path.read_text(encoding="utf-8") == "valuable content"


def test_builtin_schemas_are_available_without_plugins():
    names = {schema["name"] for schema in list_available_schemas()}
    assert {"TDG", "PEP350"} <= names


def test_schema_listing_returns_independent_definitions():
    first = list_available_schemas()
    first[0]["matching_tags"].clear()
    assert list_available_schemas()[0]["matching_tags"]


def test_typed_fields_are_canonical_when_serializing():
    tag = loads("# TODO: title\n# id=17", schema="TDG")
    updated = replace(tag, title="changed", tag_id=None, body="new body")
    recovered = loads(dumps(updated), schema="TDG")
    assert recovered.title == "changed"
    assert recovered.body == "new body"
    assert recovered.tag_id is None


def test_source_metadata_is_not_written_to_comments():
    tag = loads("# TODO: title", schema="TDG")
    tag.file_path = "secret/path.py"
    output = dumps(tag)
    assert output == "# TODO: title"
