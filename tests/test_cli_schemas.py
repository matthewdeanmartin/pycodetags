"""CLI configuration is honored regardless of working directory or option placement."""

import pytest

from pycodetags import loads
from pycodetags.__main__ import main


@pytest.mark.parametrize("before_command", [True, False])
def test_cli_uses_explicit_config_for_schema_sources_and_counter(tmp_path, monkeypatch, before_command):
    project = tmp_path / "project"
    project.mkdir()
    config = project / "pyproject.toml"
    config.write_text('[tool.pycodetags]\nschema = "TDG"\nsrc = ["sample.py"]\n', encoding="utf-8")
    path = project / "sample.py"
    path.write_text("# TODO: title\n# body", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    arguments = ["--config", str(config), "id"] if before_command else ["id", "--config", str(config)]
    assert main(arguments) == 0
    assert loads(path.read_text(encoding="utf-8"), schema="TDG").tag_id == "1"
    assert (project / ".pycodetags_ids").exists()
    assert not (tmp_path / ".pycodetags_ids").exists()


def test_cli_missing_schema_reports_an_actionable_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[tool.pycodetags]\nsrc = ["sample.py"]\n', encoding="utf-8")
    (tmp_path / "sample.py").write_text("# TODO: title", encoding="utf-8")
    assert main(["data"]) == 1
    assert "Select a schema explicitly" in capsys.readouterr().err
