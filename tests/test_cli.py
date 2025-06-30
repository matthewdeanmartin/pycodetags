# tests/test_main.py
from pathlib import Path

import pytest

from pycodetags.__main__ import main


def make_test_source_file(tmp_path: Path, content: str = "") -> Path:
    if not content:
        content = "# TODO: test comment <originator:JD origination_date:2024-01-01>"
    file = tmp_path / "example.py"
    file.write_text(content)
    return file


def test_cli_report_text_format(tmp_path, capsys):
    make_test_source_file(tmp_path)

    exit_code = main(["report", "--src", str(tmp_path), "--format", "text"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--- TODO ---" in captured.out


def test_cli_report_json_format(tmp_path, capsys):
    make_test_source_file(tmp_path)

    exit_code = main(["report", "--src", str(tmp_path), "--format", "json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"code_tag": "TODO"' in captured.out


def test_cli_report_html_format(tmp_path, capsys):
    make_test_source_file(tmp_path)

    exit_code = main(["report", "--src", str(tmp_path), "--format", "html"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "<h1>TODO</h1>" in captured.out


@pytest.mark.skip("Validate not ready yet")
def test_cli_validate_flag(tmp_path, capsys):
    make_test_source_file(tmp_path)

    exit_code = main(["report", "--src", str(tmp_path), "--validate"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "# TODO:" in captured.out  # data comment output


def test_cli_plugin_info(capsys):
    exit_code = main(["plugin-info"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "--- Loaded pycodetags Plugins ---" in captured.out


def test_cli_report_fails_on_invalid_module(capsys):
    exit_code = main(["report", "--module", "nonexistent_module"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Could not import module(s)" in captured.err


def test_cli_report_fails_on_unsupported_format(tmp_path, capsys):
    make_test_source_file(tmp_path)

    with pytest.raises(SystemExit):
        main(["report", "--src", str(tmp_path), "--format", "unsupported_format"])

    # captured = capsys.readouterr()
    # assert exit_code == 1
    # assert "Format 'unsupported_format' is not supported." in captured.err


def test_cli_main_no_args(capsys):
    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "usage:" in captured.out.lower()
