"""Exercise the installed release tool against disposable copies of our config."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("changelogmanager", reason="Release integration checks require the dev tool kacl-m")

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "component,tag,selected",
    [
        ("default", "v0.8.2", ["pyproject.toml", "pycodetags/__about__.py", "CHANGELOG.md"]),
        (
            "pycodetags-issue-tracker",
            "pycodetags-issue-tracker-v0.4.1",
            [
                "plugins/pycodetags_issue_tracker/pyproject.toml",
                "plugins/pycodetags_issue_tracker/pycodetags_issue_tracker/__about__.py",
                "plugins/pycodetags_issue_tracker/CHANGELOG.md",
            ],
        ),
    ],
)
def test_release_changes_only_component_files(tmp_path, component, tag, selected):
    """A real release must preserve siblings and the shared lockfile byte for byte."""
    files = [ROOT / "pyproject.toml", ROOT / "CHANGELOG.md", ROOT / "uv.lock", ROOT / "pycodetags/__about__.py"]
    for pattern in ("pyproject.toml", "CHANGELOG.md", "__about__.py"):
        files.extend((ROOT / "plugins").rglob(pattern))
    before = {}
    for source in files:
        relative = source.relative_to(ROOT)
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        before[relative.as_posix()] = target.read_bytes()

    def invoke(*arguments):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "changelogmanager",
                "--config",
                str(tmp_path / "pyproject.toml"),
                "--component",
                component,
                "--json",
                *arguments,
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )

    preview = json.loads(invoke("release-bump", "--version", tag, "--dry-run", "--yes").stdout)
    assert preview["tag_name"] == tag
    assert {Path(value).relative_to(tmp_path).as_posix() for value in preview["bump_candidates"]} == set(selected[:2])
    invoke("release", "--override-version", tag, "--bump-versions", "--yes")
    changed = {relative for relative, content in before.items() if (tmp_path / relative).read_bytes() != content}
    assert changed == set(selected)

    draft = json.loads(
        invoke(
            "github-release",
            "--repository",
            "owner/repo",
            "--github-token",
            "dry-run-only",
            "--version",
            tag,
            "--dry-run",
        ).stdout
    )
    assert draft["tag_name"] == tag
