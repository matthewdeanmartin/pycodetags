"""Disposable SQLite snapshots of explicitly configured Python code tags."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from pycodetags.app_config.config import CodeTagsConfig
from pycodetags.common_interfaces import string_to_data
from pycodetags.data_tags import DATA, DataTagSchema
from pycodetags.discovery import discover_files
from pycodetags.exceptions import ConfigError, PyCodeTagsError
from pycodetags.schemas import resolve_schema
from pycodetags.source_io import logical_text, read_python_source

APPLICATION_ID = 1346589767
INDEX_VERSION = 1
PARSER_VERSION = 1


class IndexStateError(PyCodeTagsError):
    """Index is missing, incompatible, or unreadable; source files remain authoritative."""


@dataclass
class RefreshResult:
    """Work counts and elapsed seconds for a complete refresh."""

    files: int = 0
    parsed: int = 0
    unchanged: int = 0
    removed: int = 0
    tags: int = 0
    bytes_read: int = 0
    discovery_seconds: float = 0
    read_seconds: float = 0
    parse_seconds: float = 0
    storage_seconds: float = 0
    total_seconds: float = 0


@dataclass
class TagIndex:
    """A project snapshot. Call refresh explicitly, then query_snapshot for cached results.

    Paths and exclusions are supplied per refresh or read from the project's pyproject.toml. An
    explicit schema argument overrides project/path configuration. Queries do not read source files.
    Results retain source fingerprints for validated mutation; local IDs need not be unique here.
    """

    root: Path
    database: Path | None = None
    schema: str | DataTagSchema | None = None

    @property
    def database_path(self) -> Path:
        return Path(self.root).resolve() / (self.database or ".pycodetags.sqlite3")

    def connect(self, create: bool = False) -> sqlite3.Connection:
        """Open only this application's database, without replacing unrelated/corrupt data."""
        path = self.database_path
        if not path.exists() and not create:
            raise IndexStateError("Index is missing; call refresh() to build it.")
        connection = sqlite3.connect(path.as_uri() + ("?mode=rwc" if create else "?mode=ro"), uri=True)
        try:
            application = connection.execute("PRAGMA application_id").fetchone()[0]
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if application != APPLICATION_ID and (tables or application or not create):
                raise IndexStateError("Not a pycodetags index; choose another database path.")
            if (
                application == APPLICATION_ID
                and connection.execute("PRAGMA user_version").fetchone()[0] != INDEX_VERSION
            ):
                raise IndexStateError("Incompatible index version; remove this disposable index and refresh.")
            connection.execute("PRAGMA foreign_keys=ON")
            if not tables and create:
                connection.executescript(f"""
                    PRAGMA application_id={APPLICATION_ID};
                    PRAGMA user_version={INDEX_VERSION};
                    CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE files (path TEXT PRIMARY KEY, digest TEXT NOT NULL, schema_digest TEXT NOT NULL);
                    CREATE TABLE tags (file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
                        ordinal INTEGER NOT NULL, tag_id TEXT, tracker TEXT, payload TEXT NOT NULL,
                        PRIMARY KEY(file_path, ordinal));
                    CREATE INDEX tags_id ON tags(tag_id);
                    CREATE INDEX tags_tracker ON tags(tracker);
                """)
            bound = connection.execute("SELECT value FROM metadata WHERE key='root'").fetchone()
            if bound and bound[0] != str(Path(self.root).resolve()):
                raise IndexStateError("Index belongs to a different project root; use another index path.")
            return connection
        except Exception:
            connection.close()
            raise

    def refresh(self, paths: Sequence[str | Path] | None = None, exclude: Sequence[str] | None = None) -> RefreshResult:
        """Read every selected file, reparse only changed snapshots, and commit the complete scan.

        Failed discovery/reads/parses roll back the snapshot. This is not a simultaneous filesystem
        snapshot: source writers must be quiescent when a consistent repository view is required.
        """
        started = perf_counter()
        root = Path(self.root).resolve()
        config = CodeTagsConfig(str(root / "pyproject.toml"))
        if isinstance(paths, (str, Path)) or isinstance(exclude, str):
            raise ConfigError("paths and exclude must be sequences, not single strings.")
        selected_paths = list(paths) if paths is not None else config.source_folders_to_scan()
        exclusions = list(exclude) if exclude is not None else config.config.get("exclude", [])
        if not selected_paths:
            raise ConfigError("Specify source paths in refresh(paths=...) or [tool.pycodetags] src.")
        if self.schema is None and not config.config.get("schema_paths"):
            resolve_schema(config.schema_for_path())
        result = RefreshResult()
        files = discover_files(root, selected_paths, exclusions)
        result.files = len(files)
        result.discovery_seconds = perf_counter() - started
        try:
            with closing(self.connect(create=True)) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                previous = {
                    row[0]: row[1:] for row in connection.execute("SELECT path, digest, schema_digest FROM files")
                }
                current = set()
                definitions = {}
                for path in files:
                    relative = path.relative_to(root).as_posix()
                    current.add(relative)
                    selection = self.schema if self.schema is not None else config.schema_for_path(path)
                    key = selection if isinstance(selection, str) else "explicit-definition"
                    if key not in definitions:
                        schema = resolve_schema(selection, path)
                        try:
                            definition = json.dumps([PARSER_VERSION, schema], sort_keys=True, ensure_ascii=False)
                        except TypeError as error:
                            raise ConfigError("Indexed schemas must be JSON-serializable definitions.") from error
                        definitions[key] = (schema, hashlib.sha256(definition.encode()).hexdigest())
                    schema, schema_digest = definitions[key]
                    read_started = perf_counter()
                    snapshot = read_python_source(path)
                    result.bytes_read += len(snapshot.raw)
                    result.read_seconds += perf_counter() - read_started
                    if previous.get(relative) == (snapshot.digest, schema_digest):
                        result.unchanged += 1
                        continue
                    parse_started = perf_counter()
                    tags = string_to_data(logical_text(snapshot.text), path, schema=schema)
                    for tag in tags:
                        tag.source_bytes_digest = snapshot.digest
                    result.parse_seconds += perf_counter() - parse_started
                    result.parsed += 1
                    storage_started = perf_counter()
                    connection.execute("DELETE FROM files WHERE path=?", (relative,))
                    connection.execute("INSERT INTO files VALUES (?, ?, ?)", (relative, snapshot.digest, schema_digest))
                    connection.executemany(
                        "INSERT INTO tags VALUES (?, ?, ?, ?, ?)",
                        [
                            (
                                relative,
                                ordinal,
                                tag.tag_id,
                                (tag.data_fields or {}).get("tracker", (tag.custom_fields or {}).get("tracker")),
                                json.dumps(tag.to_dict(), ensure_ascii=False),
                            )
                            for ordinal, tag in enumerate(tags)
                        ],
                    )
                    result.storage_seconds += perf_counter() - storage_started
                storage_started = perf_counter()
                removed = set(previous) - current
                connection.executemany("DELETE FROM files WHERE path=?", [(path,) for path in removed])
                result.removed = len(removed)
                result.tags = connection.execute("SELECT count(*) FROM tags").fetchone()[0]
                connection.executemany(
                    "INSERT OR REPLACE INTO metadata VALUES (?, ?)",
                    [
                        ("root", str(root)),
                        ("refreshed_at", datetime.now(timezone.utc).isoformat()),
                        ("parser_version", str(PARSER_VERSION)),
                        (
                            "selection",
                            json.dumps({"paths": [str(path) for path in selected_paths], "exclude": exclusions}),
                        ),
                    ],
                )
                connection.commit()
                result.storage_seconds += perf_counter() - storage_started
        except sqlite3.DatabaseError as error:
            raise IndexStateError(f"Index refresh failed: {error}. Source files were not changed.") from error
        result.total_seconds = perf_counter() - started
        return result

    def query_snapshot(
        self, *, tag_id: str | None = None, tracker: str | None = None, file_path: str | Path | None = None
    ) -> list[DATA]:
        """Query the last successful snapshot, without scanning or claiming current-source freshness.

        Filters are combined with AND. ID/tracker duplicates return all matches. Files may be root-
        relative or absolute. Returned records can be passed to the validating mutation API.
        """
        conditions, values = [], []
        for column, value in (("tag_id", tag_id), ("tracker", tracker)):
            if value is not None:
                conditions.append(column + "=?")
                values.append(value)
        if file_path is not None:
            path = Path(self.root).resolve() / file_path
            conditions.append("file_path=?")
            values.append(path.resolve().relative_to(Path(self.root).resolve()).as_posix())
        statement = (
            "SELECT payload FROM tags"
            + (" WHERE " + " AND ".join(conditions) if conditions else "")
            + " ORDER BY file_path, ordinal"
        )
        try:
            with closing(self.connect()) as connection:
                if not connection.execute("SELECT value FROM metadata WHERE key='refreshed_at'").fetchone():
                    raise IndexStateError("No successful index snapshot; call refresh().")
                records = []
                for row in connection.execute(statement, values):
                    payload = json.loads(row[0])
                    payload["offsets"] = tuple(payload["offsets"])
                    records.append(DATA(**payload))
                return records
        except (sqlite3.DatabaseError, ValueError, TypeError, KeyError) as error:
            raise IndexStateError("Index snapshot is unreadable; remove the disposable index and refresh.") from error
