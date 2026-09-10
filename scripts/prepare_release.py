"""Prepare core version files before kacl-m commits the release branch."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def prepare_version(root: Path, tag: str) -> None:
    """Update only core metadata; plugin versions belong to separate releases."""
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:[a-zA-Z0-9.+-]*)", tag):
        raise ValueError(f"Expected a core release tag such as v0.8.1, got {tag!r}")
    version = tag[1:]
    replacements = []
    for relative, field in (("pyproject.toml", "version"), ("pycodetags/__about__.py", "__version__")):
        path = root / relative
        original = path.read_text(encoding="utf-8")
        updated, count = re.subn(rf'(?m)^{field} = "[^"\n]+"$', f'{field} = "{version}"', original)
        if count != 1:
            raise ValueError(f"Expected exactly one {field} assignment in {path}")
        replacements.append((path, updated))
    for path, updated in replacements:
        path.write_text(updated, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    args = parser.parse_args()
    prepare_version(Path.cwd(), args.tag)


if __name__ == "__main__":
    main()
