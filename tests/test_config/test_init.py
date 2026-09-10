"""Configuration initialization requires the user to select a schema."""

import pytest

from pycodetags.app_config.config import CodeTagsConfig
from pycodetags.app_config.config_init import generate_pycodetags_toml_section, init_pycodetags_config


@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_initializer_writes_explicit_selection(tmp_path, monkeypatch, schema):
    monkeypatch.chdir(tmp_path)
    answers = iter(["src", schema])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    init_pycodetags_config()
    config = CodeTagsConfig()
    assert config.schema_for_path() == schema
    assert config.source_folders_to_scan() == ["src"]


@pytest.mark.parametrize("schema", ["", "1", "auto"])
def test_initializer_never_guesses_schema(tmp_path, monkeypatch, schema):
    monkeypatch.chdir(tmp_path)
    answers = iter(["src", schema])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    init_pycodetags_config()
    assert not (tmp_path / "pyproject.toml").exists()


def test_initializer_leaves_existing_config_untouched(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "pyproject.toml"
    source = '[tool.pycodetags]\nschema = "TDG"\n'
    path.write_text(source, encoding="utf-8")
    init_pycodetags_config()
    assert path.read_text(encoding="utf-8") == source


def test_generated_config_quotes_paths(tmp_path):
    path = tmp_path / "pyproject.toml"
    source = generate_pycodetags_toml_section('C:\\source with "quotes"', "PEP350")
    path.write_text(source, encoding="utf-8")
    assert CodeTagsConfig(str(path)).source_folders_to_scan() == ['C:\\source with "quotes"']
