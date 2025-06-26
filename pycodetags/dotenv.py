"""
.env file support to avoid another dependency.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _strip_inline_comment(value: str) -> str:
    """Strip unquoted inline comments starting with '#'."""
    result = []
    in_single = in_double = False

    for i, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            logger.debug(f"Stripping inline comment starting at index {i}")
            break
        result.append(char)
    return "".join(result).strip()


def _unquote(value: str) -> str:
    """Remove surrounding quotes from a string if they match."""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def load_dotenv(file_path: Path | None = None) -> None:
    """Load environment variables from a .env file into os.environ.

    Args:
        file_path (Optional[Path]): Optional custom path to a .env file.
            If not provided, defaults to ".env" in the current working directory.

    Notes:
        - Lines that are blank, comments (starting with #), or shebangs (#!) are ignored.
        - Lines must be in the form of `KEY=VALUE` or `export KEY=VALUE`.
        - Existing environment variables will not be overwritten.
        - Inline comments (starting with unquoted #) are stripped.
        - Quoted values are unwrapped.
    """
    if file_path is None:
        file_path = Path.cwd() / ".env"

    logger.info(f"Looking for .env file at: {file_path}")

    if not file_path.exists():
        logger.warning(f".env file not found at: {file_path}")
        return

    logger.info(".env file found. Starting to parse...")

    with file_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            original_line = line.rstrip("\n")
            line = line.strip()

            logger.debug(f"Line {line_number}: '{original_line}'")

            if not line or line.startswith("#") or line.startswith("#!") or line.startswith("!/"):
                logger.debug(f"Line {line_number} is blank, a comment, or a shebang. Skipping.")
                continue

            if line.startswith("export "):
                line = line[len("export ") :].strip()

            if "=" not in line:
                logger.warning(f"Line {line_number} is not a valid assignment. Skipping: '{original_line}'")
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                logger.warning(f"Line {line_number} has empty key. Skipping: '{original_line}'")
                continue

            value = _strip_inline_comment(value)
            value = _unquote(value)

            if key in os.environ:
                logger.info(f"Line {line_number}: Key '{key}' already in os.environ. Skipping.")
                continue

            os.environ[key] = value
            logger.info(f"Line {line_number}: Loaded '{key}' = '{value}'")


if __name__ == "__main__":
    load_dotenv()
