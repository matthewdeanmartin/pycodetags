"""Expected release-facing failures have concise diagnostics and preserve state."""

import sqlite3
from contextlib import closing

import pytest

from pycodetags import TagIndex
from pycodetags.__main__ import main
from pycodetags.index import IndexStateError


@pytest.mark.parametrize("config", ["[broken", '[tool.pycodetags]\nsrc="src"', "[tool.pycodetags]\nexclude=1"])
def test_malformed_config_is_a_cli_error(tmp_path, capsys, config):
    path = tmp_path / "bad.toml"
    path.write_text(config, encoding="utf-8")
    assert main(["data", "--config", str(path)]) == 1
    error = capsys.readouterr().err
    assert error.startswith("Error:") and "Traceback" not in error


def test_missing_id_source_is_a_cli_error(tmp_path, capsys):
    config = tmp_path / "pyproject.toml"
    config.write_text('[tool.pycodetags]\nschema="TDG"\n', encoding="utf-8")
    assert main(["id", str(tmp_path / "missing.py"), "--config", str(config)]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_invalid_encoding_is_a_cli_error(tmp_path, capsys):
    config = tmp_path / "pyproject.toml"
    config.write_text('[tool.pycodetags]\nschema="TDG"\n', encoding="utf-8")
    source = tmp_path / "bad.py"
    source.write_bytes(b"# coding: imaginary-codec\n# TODO: bad\n")
    assert main(["data", "--src", str(source), "--config", str(config)]) == 1
    assert "Cannot decode" in capsys.readouterr().err


def test_index_lock_failure_does_not_overwrite_snapshot(tmp_path, monkeypatch):
    path = tmp_path / "source.py"
    path.write_bytes(b"# TODO: old\n")
    index = TagIndex(tmp_path, schema="TDG")
    index.refresh(paths=[path])
    connect = sqlite3.connect
    with closing(connect(index.database_path)) as writer:
        writer.execute("BEGIN EXCLUSIVE")

        def impatient(*args, **kwargs):
            kwargs["timeout"] = 0.01
            return connect(*args, **kwargs)

        monkeypatch.setattr("pycodetags.index.sqlite3.connect", impatient)
        with pytest.raises(IndexStateError, match="locked"):
            index.refresh(paths=[path])
        writer.rollback()
    assert index.query_snapshot()[0].title == "old"
