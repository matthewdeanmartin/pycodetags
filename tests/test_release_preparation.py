"""Core release preparation must not bump independently versioned plugins."""

import runpy
from pathlib import Path

import pytest

prepare_version = runpy.run_path(str(Path(__file__).parents[1] / "scripts/prepare_release.py"))["prepare_version"]


def test_core_version_preparation(tmp_path):
    (tmp_path / "pycodetags").mkdir()
    (tmp_path / "plugins").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.8.0"\n', encoding="utf-8")
    about = tmp_path / "pycodetags/__about__.py"
    about.write_text('__version__ = "0.8.0"\n', encoding="utf-8")
    plugin = tmp_path / "plugins/__about__.py"
    plugin.write_text('__version__ = "0.4.0"\n', encoding="utf-8")
    prepare_version(tmp_path, "v0.8.1")
    assert 'version = "0.8.1"' in (tmp_path / "pyproject.toml").read_text()
    assert '__version__ = "0.8.1"' in about.read_text()
    assert '__version__ = "0.4.0"' in plugin.read_text()


def test_invalid_metadata_does_not_partially_update(tmp_path):
    (tmp_path / "pycodetags").mkdir()
    project = tmp_path / "pyproject.toml"
    original = '[project]\nversion = "0.8.0"\n'
    project.write_text(original, encoding="utf-8")
    (tmp_path / "pycodetags/__about__.py").write_text("# Missing version\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one"):
        prepare_version(tmp_path, "v0.8.1")
    assert project.read_text() == original


@pytest.mark.parametrize("tag", ["0.8.1", "pycodetags-issue-tracker-v0.4.1", "v0.8.1\nextra"])
def test_reject_non_core_tags(tmp_path, tag):
    with pytest.raises(ValueError, match="core release tag"):
        prepare_version(tmp_path, tag)
