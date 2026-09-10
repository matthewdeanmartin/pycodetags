"""Exercise an installed release candidate with only its declared runtime dependencies."""

import argparse
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pycodetags
from pycodetags import DATA, TagIndex, apply_mutations, dumps, inspect_file, loads, update_tags


def cli(*args, success=True):
    result = subprocess.run([sys.executable, "-I", "-m", "pycodetags", *args], text=True, capture_output=True)
    assert (result.returncode == 0) == success, (args, result.stdout, result.stderr)
    assert "Traceback" not in result.stderr, result.stderr
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugins", action="store_true")
    args = parser.parse_args()
    os.environ["PYCODETAGS_NO_OPEN_BROWSER"] = "1"
    assert Path(pycodetags.__file__).is_relative_to(Path(sys.prefix)), pycodetags.__file__
    import pycodetags.__about__ as metadata

    assert importlib.metadata.version("pycodetags") == metadata.__version__
    assert not importlib.util.find_spec("pytest"), "Smoke environment must contain runtime dependencies only"
    for schema in ("TDG", "PEP350"):
        path = Path(schema + ".py")
        path.write_bytes(
            (
                dumps(DATA(code_tag="TODO", title="title", body="body\n\nlast", tag_id="17"), schema=schema) + "\n"
            ).encode()
        )
        old = inspect_file(path, schema=schema)[0]
        update_tags(path, [(old, replace(old, title="updated"))])
        assert inspect_file(path, schema=schema)[0].body == "body\n\nlast"
        index = TagIndex(Path.cwd(), database=Path(schema + ".sqlite"), schema=schema)
        index.refresh(paths=[path])
        assert index.query_snapshot(tag_id="17")[0].title == "updated"
        apply_mutations(path, [(index.query_snapshot()[0], None)])
        assert index.refresh(paths=[path]).tags == 0
    Path("pyproject.toml").write_text('[tool.pycodetags]\nschema="TDG"\nsrc=["sample.py"]\n', encoding="utf-8")
    Path("sample.py").write_bytes(b"# TODO: sample\n# issue=100\n# description\n")
    cli("--help")
    cli("id", "sample.py")
    report = cli("data", "--format", "json")
    assert json.loads(report.stdout)[0]["title"] == "sample"
    cli("id", "missing.py", success=False)
    Path("bad.toml").write_text("[broken", encoding="utf-8")
    cli("data", "--config", "bad.toml", success=False)
    Path("bad.py").write_bytes(b"# coding: utf-8\n# TODO: \xff\n")
    cli("data", "--src", "bad.py", success=False)
    if args.plugins:
        from pycodetags_issue_tracker.converters import convert_data_to_TODO

        from pycodetags.plugin_manager import get_plugin_manager

        manager = get_plugin_manager()
        manager.check_pending()
        names = {schema["name"] for schema in pycodetags.list_available_schemas()}
        assert {"TDG", "PEP350", "TODO", "discussion"} <= names
        discussion = loads("# QUESTION: Why? <author=alice>", schema="discussion")
        assert discussion.title == "Why?"
        issue = convert_data_to_TODO(inspect_file("sample.py", schema="TDG")[0])
        assert issue.issue == "100" and issue.tag_id is not None
        cli("issues", "--format", "text")
        cli("issues", "--format", "html", "--output", "report")
        assert (Path("report") / "index.html").is_file()
        Path("sample.js").write_bytes(b"// TODO: JavaScript\n// issue=100\n// detail\nconst value = 1;\n")
        assert json.loads(cli("data", "--src", "sample.js", "--format", "json").stdout)[0]["title"] == "JavaScript"
    print("Installed artifact smoke passed", sys.version.split()[0], "plugins=" + str(args.plugins))


if __name__ == "__main__":
    main()
