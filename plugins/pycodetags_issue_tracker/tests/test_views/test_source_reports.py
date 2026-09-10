"""Reports must retain parsed tasks without enabling runtime actions."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("format_name", ["todomd", "changelog"])
@pytest.mark.parametrize("schema", ["TDG", "PEP350"])
def test_reports_include_source_tasks(tmp_path, schema, format_name):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pycodetags]\nschema = "' + schema + '"\nsrc = ["src"]\n'
        'closed_status = ["done"]\nvalid_status = ["todo", "done"]\n',
        encoding="utf-8",
    )
    source = tmp_path / "src"
    source.mkdir()
    tasks = [
        ("Explain invalid dates", "status=todo priority=high"),
        ("Handle empty rows", "release=1.0.0 change_type=Fixed closed_date=2026-09-10"),
        ("Explain supported dates", "status=done release=1.0.0 change_type=fixed"),
        ("Unclassified completion", "status=done release=1.0.0"),
        ("Review import rules", "status=review"),
        ("Document the importer", ""),
    ]
    for number, (title, properties) in enumerate(tasks):
        text = f"# TODO: {title}\n# {properties}\n" if schema == "TDG" else f"# TODO: {title} <{properties}>\n"
        (source / f"task{number}.py").write_text(text, encoding="utf-8")

    def report(format_name):
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "pycodetags", "issues", "--format", format_name],
            cwd=tmp_path,
            env={**os.environ, "PYCODETAGS_NO_OPEN_BROWSER": "1"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return result.stdout

    output = report(format_name)
    if format_name == "todomd":
        for title, _ in tasks:
            assert output.count(title) == 1
        assert "- [ ] Explain invalid dates" in output
        assert "- [x] Handle empty rows" in output
        assert "- [x] Explain supported dates" in output
    else:
        assert "## [1.0.0] - 2026-09-10" in output
        assert "### Fixed" in output
        assert "- Handle empty rows" in output
        assert "- Explain supported dates" in output
        assert "### Unclassified\n- Unclassified completion" in output
        assert "Explain invalid dates" not in output
