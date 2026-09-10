"""Selection is explicit and path rules never resolve ambiguity by guessing."""

from copy import deepcopy

import pytest

from pycodetags import DATA, PEP350Schema, TDGSchema, dumps, inspect_file, loads
from pycodetags.aggregate import aggregate_all_kinds_multiple_input
from pycodetags.app_config import CodeTagsConfig
from pycodetags.data_tags.data_tags_parsers import iterate_comments
from pycodetags.exceptions import ConfigError, SchemaError


def configure(root, text):
    path = root / "pyproject.toml"
    path.write_text("[tool.pycodetags]\n" + text, encoding="utf-8")
    CodeTagsConfig.set_instance(CodeTagsConfig(str(path)))
    return path


@pytest.mark.parametrize("operation", ["load", "dump", "inspect"])
def test_unconfigured_operations_fail_even_when_syntax_looks_obvious(tmp_path, monkeypatch, operation):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "sample.py"
    path.write_text("# TODO: title <issue=100>\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Select a schema explicitly"):
        if operation == "load":
            loads(path.read_text(encoding="utf-8"))
        elif operation == "dump":
            dumps(DATA(code_tag="TODO", title="title"))
        else:
            inspect_file(path)


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_explicit_api_schema_works_without_a_project(tmp_path, monkeypatch, schema):
    monkeypatch.chdir(tmp_path)
    tag = DATA(code_tag="TODO", title="title", body="body")
    recovered = loads(dumps(tag, schema=schema), schema=schema)
    assert recovered.title == "title"
    assert recovered.body == "body"


def test_project_choice_controls_parsing_without_content_detection(tmp_path):
    configure(tmp_path, 'schema = "TDG"\n')
    tag = loads("# TODO: title <issue=100>")
    assert tag.title == "title <issue=100>"
    assert "issue" not in tag.data_fields
    assert loads("# TODO: title\n# issue=100", schema="PEP350") is None


def test_path_rules_and_project_choice_apply_to_entire_files(tmp_path):
    configure(tmp_path, 'schema = "TDG"\n[[tool.pycodetags.schema_paths]]\npath = "legacy/*.py"\nschema = "PEP350"\n')
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "a.py").write_text("# TODO: old <id=1>\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("# TODO: new\n# id=2\n", encoding="utf-8")
    tags = aggregate_all_kinds_multiple_input([], [str(tmp_path)])
    assert {(tag.title, tag.tag_id, tag.original_schema) for tag in tags} == {
        ("old", "1", "PEP350"),
        ("new", "2", "TDG"),
    }


def test_rules_only_project_requires_every_file_to_match(tmp_path):
    configure(tmp_path, '[[tool.pycodetags.schema_paths]]\npath = "selected.py"\nschema = "TDG"\n')
    path = tmp_path / "other.py"
    path.write_text("# TODO: title", encoding="utf-8")
    with pytest.raises(ConfigError):
        inspect_file(path)
    assert inspect_file(path, schema="TDG")[0].title == "title"


def test_overlapping_rules_fail_even_if_they_name_the_same_schema(tmp_path):
    configure(
        tmp_path,
        'schema = "TDG"\n[[tool.pycodetags.schema_paths]]\npath = "*.py"\nschema = "TDG"\n'
        '[[tool.pycodetags.schema_paths]]\npath = "a.py"\nschema = "TDG"\n',
    )
    path = tmp_path / "a.py"
    path.write_text("# TODO: title", encoding="utf-8")
    with pytest.raises(ConfigError, match="Overlapping"):
        inspect_file(path)


def test_unknown_schema_fails_instead_of_being_ignored():
    with pytest.raises(SchemaError, match="Unknown"):
        loads("# TODO: title", schema="typo")


def test_custom_schema_requires_an_explicit_format():
    schema = deepcopy(TDGSchema)
    del schema["format"]
    with pytest.raises(SchemaError, match="format explicitly"):
        loads("# TODO: title", schema=schema)


def test_custom_schema_survives_serialization_without_configuration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    schema = dict(deepcopy(TDGSchema), name="Tasks", matching_tags=["TASK"])
    tag = loads("# TASK: title\n# category=core", schema=schema)
    schema["matching_tags"].clear()
    assert dumps(tag).startswith("# TASK: title")
    assert tag.schema["matching_tags"] == ["TASK"]


@pytest.mark.parametrize("schemas", [[], [TDGSchema, PEP350Schema], [TDGSchema, TDGSchema]])
def test_pipeline_requires_one_schema_per_file(schemas):
    with pytest.raises(SchemaError, match="exactly one"):
        list(iterate_comments("# TODO: title", None, schemas, False))


def test_folk_fallback_is_not_silently_added():
    with pytest.raises(SchemaError, match="Folk fallback"):
        loads("# TODO: title", schema="TDG", include_folk_tags=True)
