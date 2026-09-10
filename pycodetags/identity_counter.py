"""
Per-project counter that hands out short, stable local ids (``id=N``) for data tags.

The counter is stored at ``<project_root>/.pycodetags_ids`` as a small, human-diffable JSON object.
Unlike the cache, this file is **meant to be committed** to version control so that ids stay stable
across clones and CI. Source code is the source of truth for which ids exist; this counter is a
convenience for allocating the *next* id and detecting drift.

See ``spec/id_and_tdg.md`` Part 1.3.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from pycodetags.exceptions import DataTagError
from pycodetags.utils.cache_utils import find_project_root

logger = logging.getLogger(__name__)

COUNTER_FILENAME = ".pycodetags_ids"
COUNTER_VERSION = 1


class IdCounter:
    """Allocates monotonically increasing local ids and records what they were allocated for."""

    def __init__(self, path: Path, next_id: int = 1, allocated: dict[str, str] | None = None) -> None:
        self.path = path
        self.next_id = next_id
        # id (as string) -> content_identity at time of allocation
        self.allocated: dict[str, str] = allocated or {}

    @classmethod
    def path_for(cls, root: Path | None = None) -> Path:
        """Return the counter file path for the given (or auto-detected) project root."""
        root = root or find_project_root()
        return root / COUNTER_FILENAME

    @classmethod
    def load(cls, root: Path | None = None) -> IdCounter:
        """Load a valid counter; only a missing file permits starting a fresh counter."""
        path = cls.path_for(root)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls(path=path)
        except (ValueError, OSError) as e:
            raise DataTagError(f"Cannot read id counter {path}; refusing to reset existing IDs.") from e

        if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != COUNTER_VERSION:
            raise DataTagError(f"Invalid id counter version in {path}.")
        allocated = data.get("allocated")
        next_id = data.get("next_id")
        if type(next_id) is not int or next_id < 1 or not isinstance(allocated, dict):
            raise DataTagError(f"Invalid id counter structure in {path}.")
        for tag_id, content_id in allocated.items():
            validate_local_id(tag_id)
            if not isinstance(content_id, str) or not content_id:
                raise DataTagError(f"Invalid content identity for id {tag_id!r} in {path}.")
        counter = cls(path=path, next_id=next_id, allocated=allocated)
        counter.reconcile_next_id()
        return counter

    def reconcile_next_id(self) -> None:
        """Ensure ``next_id`` is greater than every id we already know about."""
        if self.allocated:
            max_known = max(int(k) for k in self.allocated)
            if self.next_id <= max_known:
                self.next_id = max_known + 1

    @property
    def known_ids(self) -> set[str]:
        """The set of ids that have been allocated."""
        return set(self.allocated.keys())

    def record_existing(self, tag_id: str, content_id: str) -> None:
        """Record an id already present in source so the counter does not hand it out again.

        Source is the source of truth: if a tag in source already has ``id=42``, we adopt it and bump
        ``next_id`` past it. Existing records are not overwritten with a different content id silently
        (a mismatch is logged, since it may indicate the tag text changed since allocation).
        """
        tag_id = str(tag_id)
        validate_local_id(tag_id)
        existing = self.allocated.get(tag_id)
        if existing is not None and existing != content_id:
            logger.debug(
                "id %s content changed: %s -> %s (tag text edited since allocation)", tag_id, existing, content_id
            )
        self.allocated[tag_id] = content_id
        if tag_id.isdigit() and int(tag_id) >= self.next_id:
            self.next_id = int(tag_id) + 1

    def allocate(self, content_id: str) -> str:
        """Allocate the next id, record it against ``content_id``, and return it as a string."""
        new_id = str(self.next_id)
        self.next_id += 1
        self.allocated[new_id] = content_id
        return new_id

    def save(self) -> None:
        """Atomically write the counter to disk (temp file + ``os.replace``)."""
        payload = {
            "version": COUNTER_VERSION,
            "next_id": self.next_id,
            # Sort for a stable, diff-friendly file.
            "allocated": {k: self.allocated[k] for k in sorted(self.allocated, key=lambda s: (len(s), s))},
        }
        text = json.dumps(payload, indent=2) + "\n"
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", prefix=".pycodetags-ids-", suffix=".tmp", dir=self.path.parent, delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def validate_local_id(tag_id: str) -> None:
    """Require a positive decimal ID in canonical form to avoid ambiguous keys such as 01."""
    if not isinstance(tag_id, str) or not tag_id.isascii() or not tag_id.isdecimal() or tag_id.startswith("0"):
        raise DataTagError(f"Invalid local id {tag_id!r}; expected a positive decimal integer without leading zeros.")
