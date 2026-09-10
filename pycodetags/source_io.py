"""Python source snapshots and single-writer file replacement."""

from __future__ import annotations

import hashlib
import io
import os
import stat
import tempfile
import tokenize
from dataclasses import dataclass
from pathlib import Path

from pycodetags.exceptions import DataTagError, FileParsingError


def logical_text(text: str) -> str:
    """Normalize physical line endings, without changing any other whitespace."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def text_digest(text: str) -> str:
    """Fingerprint text even when a caller has used universal-newline reading."""
    return hashlib.sha256(logical_text(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceSnapshot:
    """One byte-preserving read of a Python file."""

    path: Path
    raw: bytes
    text: str
    encoding: str

    digest: str


def read_python_source(path: str | os.PathLike[str]) -> SourceSnapshot:
    """Decode the Python encoding declaration, retaining BOM and newline information."""
    path = Path(path).absolute()
    raw = path.read_bytes()
    header = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(header).readline)
        text = raw.decode(encoding)
    except (SyntaxError, UnicodeError, LookupError) as error:
        raise FileParsingError(f"Cannot decode Python source {path}: {error}") from error
    if text.encode(encoding) != raw:
        raise DataTagError(f"Source encoding cannot be preserved exactly: {path}")
    return SourceSnapshot(path, raw, text, encoding, hashlib.sha256(raw).hexdigest())


def replace_source(snapshot: SourceSnapshot, text: str) -> None:
    """Replace once after a byte recheck; callers must provide exclusive writer ownership.

    A concurrent edit between the final check and os.replace cannot be excluded without a lock.
    Symlinks and multiply linked files are rejected to avoid changing link semantics.
    """
    encoded = text.encode(snapshot.encoding)
    if encoded == snapshot.raw:
        return
    path = snapshot.path
    if path.is_symlink() or path.stat().st_nlink > 1:
        raise DataTagError("Mutation requires a regular source file with a single link.")
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        if path.is_symlink() or path.read_bytes() != snapshot.raw:
            raise DataTagError("Tag mismatch: source changed while preparing mutations; reparse and retry.")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            # A read-only source mode may have been copied before a failed replacement.
            os.chmod(temporary, stat.S_IWRITE | stat.S_IREAD)
            temporary.unlink()
