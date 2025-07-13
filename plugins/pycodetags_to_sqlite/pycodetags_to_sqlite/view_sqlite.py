"""
Export code tags to a SQLite database.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from pycodetags.data_tags.data_tags_classes import DATA

logger = logging.getLogger(__name__)


def _create_and_populate_denormalized_table(cursor: sqlite3.Cursor, found: list[DATA]):
    """
    Creates and populates a single denormalized table using DATA.to_dict().

    Args:
        cursor (sqlite3.Cursor): The database cursor.
        found (list[DATA]): The list of DATA items.
    """
    cursor.execute("DROP TABLE IF EXISTS code_tags_denormalized")
    logger.debug("Dropped existing denormalized table if it existed.")

    # Get all possible keys for columns by inspecting all items
    all_dicts = [item.to_dict() for item in found]
    if not all_dicts:
        logger.warning("No DATA items found to export to denormalized table.")
        return

    all_keys: set[str] = set()
    for d in all_dicts:
        all_keys.update(d.keys())

    # Create table with all possible columns
    sorted_keys = sorted(list(all_keys))
    columns_str = ", ".join([f'"{col}" TEXT' for col in sorted_keys])
    create_table_sql = f"CREATE TABLE code_tags_denormalized (id INTEGER PRIMARY KEY, {columns_str})"
    logger.debug(f"Creating denormalized table with SQL: {create_table_sql}")
    cursor.execute(create_table_sql)

    # Prepare insert statement
    cols_for_insert = ", ".join([f'"{col}"' for col in sorted_keys])
    placeholders = ", ".join(["?"] * len(sorted_keys))
    insert_sql = f"INSERT INTO code_tags_denormalized ({cols_for_insert}) VALUES ({placeholders})"  # nosec
    logger.debug(f"Prepared insert statement: {insert_sql}")

    # Insert data
    for d in all_dicts:
        values: list[Any | None] = []
        for key in sorted_keys:
            val = d.get(key)
            # SQLite can handle basic types, but lists/dicts/tuples need to be stored as strings.
            if isinstance(val, (list, dict, tuple)):
                values.append(str(val))
            else:
                values.append(val)
        cursor.execute(insert_sql, values)
    logger.info(f"Populated denormalized table with {len(found)} rows.")


def _create_and_populate_normalized_tables(cursor: sqlite3.Cursor, found: list[DATA]):
    """
    Creates and populates a set of normalized tables with foreign key relationships.

    Args:
        cursor (sqlite3.Cursor): The database cursor.
        found (list[DATA]): The list of DATA items.
    """
    # Drop existing tables in reverse order of dependency
    logger.debug("Dropping existing normalized tables.")
    cursor.execute("DROP TABLE IF EXISTS unprocessed_defaults")
    cursor.execute("DROP TABLE IF EXISTS default_fields")
    cursor.execute("DROP TABLE IF EXISTS custom_fields")
    cursor.execute("DROP TABLE IF EXISTS data_fields")
    cursor.execute("DROP TABLE IF EXISTS tags")

    # Create tables
    logger.debug("Creating normalized tables.")
    cursor.execute(
        """
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY,
            code_tag TEXT,
            comment TEXT,
            file_path TEXT,
            line_number INTEGER,
            original_text TEXT,
            original_schema TEXT,
            offsets_start_line INTEGER,
            offsets_start_char INTEGER,
            offsets_end_line INTEGER,
            offsets_end_char INTEGER
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE data_fields (
            id INTEGER PRIMARY KEY,
            tag_id INTEGER,
            field_name TEXT,
            field_value TEXT,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE custom_fields (
            id INTEGER PRIMARY KEY,
            tag_id INTEGER,
            field_name TEXT,
            field_value TEXT,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE default_fields (
            id INTEGER PRIMARY KEY,
            tag_id INTEGER,
            field_name TEXT,
            field_value TEXT,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE unprocessed_defaults (
            id INTEGER PRIMARY KEY,
            tag_id INTEGER,
            value TEXT,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        )
    """
    )
    logger.debug("Normalized tables created successfully.")

    # Populate tables
    for item in found:
        offsets = item.offsets or (None, None, None, None)
        cursor.execute(
            """
            INSERT INTO tags (code_tag, comment, file_path, line_number, original_text, original_schema,
                              offsets_start_line, offsets_start_char, offsets_end_line, offsets_end_char)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                item.code_tag,
                item.comment,
                item.file_path,
                offsets[0],
                item.original_text,
                item.original_schema,
                offsets[0],
                offsets[1],
                offsets[2],
                offsets[3],
            ),
        )
        tag_id = cursor.lastrowid

        if item.data_fields:
            for key, value in item.data_fields.items():
                cursor.execute(
                    "INSERT INTO data_fields (tag_id, field_name, field_value) VALUES (?, ?, ?)",
                    (tag_id, key, str(value)),
                )

        if item.custom_fields:
            for key, value in item.custom_fields.items():
                cursor.execute(
                    "INSERT INTO custom_fields (tag_id, field_name, field_value) VALUES (?, ?, ?)",
                    (tag_id, key, str(value)),
                )

        if item.default_fields:
            for key, value in item.default_fields.items():
                cursor.execute(
                    "INSERT INTO default_fields (tag_id, field_name, field_value) VALUES (?, ?, ?)",
                    (tag_id, key, str(value)),
                )

        if item.unprocessed_defaults:
            for value in item.unprocessed_defaults:
                cursor.execute("INSERT INTO unprocessed_defaults (tag_id, value) VALUES (?, ?)", (tag_id, value))
    logger.info(f"Populated normalized tables with {len(found)} tags and their fields.")


def export_sqlite(found: list[DATA], db_path: str, denormalized: bool = True, normalized: bool = True) -> None:
    """
    Exports found DATA items to a SQLite database, creating both denormalized and normalized tables.

    Args:
        found (list[DATA]): The collected DATA items.
        db_path (str): The path to the SQLite database file.
        denormalized (bool): If True, creates a single denormalized table.
        normalized (bool): If True, creates a set of normalized tables.
    """
    if not found:
        logger.warning("No DATA items found to export. Aborting SQLite export.")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logger.info(f"Connected to SQLite database at {db_path}")

        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys = ON;")

        if denormalized:
            _create_and_populate_denormalized_table(cursor, found)

        if normalized:
            _create_and_populate_normalized_tables(cursor, found)

        conn.commit()
        logger.info(f"Data successfully committed to {db_path}")

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed.")
