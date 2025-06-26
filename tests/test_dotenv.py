from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from pycodetags.dotenv import load_dotenv


@contextmanager
def cleared_env_vars(*keys: str) -> Generator[None]:
    """Temporarily clear specific environment variables during a test."""
    backup = {k: os.environ[k] for k in keys if k in os.environ}
    for k in keys:
        os.environ.pop(k, None)
    try:
        yield
    finally:
        os.environ.update(backup)


def test_basic_assignment(tmp_path: Path) -> None:
    """Test simple key=value lines."""
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=bar\nBAZ=qux\n", encoding="utf-8")

    with cleared_env_vars("FOO", "BAZ"):
        load_dotenv(dotenv)
        assert os.environ["FOO"] == "bar"
        assert os.environ["BAZ"] == "qux"


def test_export_lines(tmp_path: Path) -> None:
    """Test 'export KEY=VALUE' syntax."""
    dotenv = tmp_path / ".env"
    dotenv.write_text("export FOO=bar\nexport BAZ=qux\n", encoding="utf-8")

    with cleared_env_vars("FOO", "BAZ"):
        load_dotenv(dotenv)
        assert os.environ["FOO"] == "bar"
        assert os.environ["BAZ"] == "qux"


def test_ignores_comments_blanks_shebang(tmp_path: Path) -> None:
    """Ensure blank lines, comments, and shebangs are ignored."""
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        """
# Comment
FOO=bar

#! /usr/bin/env python3
# Another comment
BAR=baz
        """,
        encoding="utf-8",
    )

    with cleared_env_vars("FOO", "BAR"):
        load_dotenv(dotenv)
        assert os.environ["FOO"] == "bar"
        assert os.environ["BAR"] == "baz"


def test_does_not_override_existing_env(tmp_path: Path) -> None:
    """Ensure existing os.environ values are not overwritten."""
    dotenv = tmp_path / ".env"
    dotenv.write_text("FOO=newvalue\n", encoding="utf-8")

    os.environ["FOO"] = "original"

    try:
        load_dotenv(dotenv)
        assert os.environ["FOO"] == "original"
    finally:
        del os.environ["FOO"]


def test_ignores_invalid_lines(tmp_path: Path) -> None:
    """Lines without = should be ignored."""
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        """
NO_EQUALS
export
=
BAD = 
= no_key
VALID=okay
""",
        encoding="utf-8",
    )

    with cleared_env_vars("VALID"):
        load_dotenv(dotenv)
        assert os.environ["VALID"] == "okay"
        assert "NO_EQUALS" not in os.environ
        # assert "BAD" not in os.environ # this is actually okay.
        assert "" not in os.environ


def test_crazy_dotenv(tmp_path: Path) -> None:
    """Stress test with edge cases."""
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        r"""
# Leading/trailing whitespace
   FOO = bar   
BAR=baz   
export    ZAZ   = 123

# Quotes and special characters (not parsed but allowed as-is)
QUOTED="some value"
ESCAPED=some\ value\ with\ spaces
SPECIAL= !@#$%^&*()_+

# Comments at end of line
INLINE=ok # this should not be part of the value

# Malformed lines
=missing_key
missing_value=
no_equals
export

#! shebang
#!/usr/bin/env bash

export EXPORT_THIS=yes
""",
        encoding="utf-8",
    )

    keys = ["FOO", "BAR", "ZAZ", "QUOTED", "ESCAPED", "SPECIAL", "INLINE", "EXPORT_THIS"]
    with cleared_env_vars(*keys):
        load_dotenv(dotenv)
        assert os.environ["FOO"] == "bar"
        assert os.environ["BAR"] == "baz"
        assert os.environ["ZAZ"] == "123"
        assert os.environ["QUOTED"] == "some value"
        assert os.environ["ESCAPED"] == r"some\ value\ with\ spaces"
        assert os.environ["SPECIAL"] == "!@"  # comment symbol without quotes
        assert os.environ["missing_value"] == ""
        assert os.environ["EXPORT_THIS"] == "yes"

        # Make sure invalid keys didn't leak in
        assert "missing_key" not in os.environ
        assert "no_equals" not in os.environ

        assert os.environ["INLINE"] == "ok"


def test_missing_file(tmp_path: Path) -> None:
    """Ensure nothing crashes if file doesn't exist."""
    dotenv = tmp_path / "nonexistent.env"
    load_dotenv(dotenv)


def test_inline_comments_and_quoting(tmp_path: Path) -> None:
    """Test inline comments and quoting behavior."""
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        """
INLINE=ok # comment should be ignored
HASHED=abc#123
QUOTED1="abc#123"
QUOTED2='abc#123'
        """,
        encoding="utf-8",
    )

    with cleared_env_vars("INLINE", "HASHED", "QUOTED1", "QUOTED2"):
        load_dotenv(dotenv)

        assert os.environ["INLINE"] == "ok"
        assert os.environ["HASHED"] == "abc"  # comment symbol, no quotes
        assert os.environ["QUOTED1"] == "abc#123"
        assert os.environ["QUOTED2"] == "abc#123"
