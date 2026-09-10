"""Build and smoke-test the core and functional plugin release candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {
    "core": ROOT,
    **{
        name: ROOT / "plugins" / name
        for name in ("pycodetags_issue_tracker", "pycodetags_chat", "pycodetags_universal")
    },
}


def run(*args, cwd=None):
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def build(output):
    for name, project in PROJECTS.items():
        run("uv", "build", str(project), "--out-dir", output / name, "--no-sources", cwd=ROOT)
    run(sys.executable, ROOT / "scripts/verify_distribution.py", output / "core")
    manifest = {
        str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.glob("*/*"))
        if path.suffix in (".whl", ".gz")
    }
    (output / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def smoke(output, kind):
    artifacts = []
    for name in PROJECTS:
        matches = list((output / name).glob("*.whl" if kind == "wheel" else "*.tar.gz"))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one {kind} for {name}: {matches}")
        artifacts.extend(matches)
    with tempfile.TemporaryDirectory(prefix="pycodetags-release-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        core_work = root / "core"
        core_work.mkdir()
        run("uv", "pip", "install", "--python", python, artifacts[0], cwd=root)
        run(python, "-I", ROOT / "scripts/artifact_smoke.py", cwd=core_work)
        # Install the exact candidates together so dependency resolution cannot select an older core.
        run("uv", "pip", "install", "--python", python, *artifacts, cwd=root)
        plugin_work = root / "plugins"
        plugin_work.mkdir()
        run(python, "-I", ROOT / "scripts/artifact_smoke.py", "--plugins", cwd=plugin_work)
        run("uv", "pip", "check", "--python", python, cwd=root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "smoke", "all", "verify-tag"])
    parser.add_argument("--output", type=Path, default=ROOT / ".build/release-candidates")
    parser.add_argument("--kind", choices=["wheel", "sdist", "both"], default="both")
    parser.add_argument("--project", choices=list(PROJECTS), default="core")
    parser.add_argument("--tag")
    args = parser.parse_args()
    if args.command == "verify-tag":
        import tomllib

        metadata = tomllib.loads((PROJECTS[args.project] / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        expected = ("v" if args.project == "core" else metadata["name"] + "-v") + metadata["version"]
        if args.tag != expected:
            raise RuntimeError(f"Release tag must match committed metadata: expected {expected!r}, got {args.tag!r}")
        print(f"Verified release tag {expected}")
        return
    output = args.output.resolve()
    if args.command in ("build", "all"):
        build(output)
    if args.command in ("smoke", "all"):
        for kind in (["wheel", "sdist"] if args.kind == "both" else [args.kind]):
            smoke(output, kind)


if __name__ == "__main__":
    main()
