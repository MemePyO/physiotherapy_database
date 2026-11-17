"""Reusable helpers for database migration tests.

The helpers keep migration tests focused on behaviour instead of repeating the
SQL boilerplate needed to inspect a schema or temporarily register a migration.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Callable, Iterable, Iterator

import data.migrations as migrations

Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]


def table_names(conn: sqlite3.Connection) -> set[str]:
    """Return every user table in the database."""
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(row[0]) for row in rows if not str(row[0]).startswith("sqlite_")}


def index_names(conn: sqlite3.Connection, table: str | None = None) -> set[str]:
    """Return user-created index names, optionally limited to one table."""
    if table is None:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    else:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?", (table,)
        ).fetchall()
    return {str(row[0]) for row in rows if not str(row[0]).startswith("sqlite_")}


def column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return the columns of *table*."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row[1]) for row in rows}


@contextlib.contextmanager
def temporary_migrations(entries: Iterable[Migration]) -> Iterator[None]:
    """Register migrations for one test and restore the registry afterwards."""
    saved: dict[int, tuple[str, Callable[[object], None]] | None] = {}
    try:
        for version, description, fn in entries:
            saved[version] = migrations.MIGRATIONS.get(version)
            migrations.register(version, description, fn)
        yield
    finally:
        for version, original in saved.items():
            if original is None:
                migrations.MIGRATIONS.pop(version, None)
            else:
                migrations.MIGRATIONS[version] = original


def downgrade_database(
    dbfile: str,
    version: int = 1,
    drop_indexes: Iterable[str] | None = None,
) -> None:
    """Approximate an older database by dropping indexes and lowering the version."""
    conn = sqlite3.connect(dbfile)
    try:
        names = list(drop_indexes) if drop_indexes is not None else sorted(index_names(conn))
        for name in names:
            conn.execute(f"DROP INDEX IF EXISTS {name}")
        conn.execute(f"PRAGMA user_version = {int(version)}")
        conn.commit()
    finally:
        conn.close()


def assert_schema_integrity(
    conn: sqlite3.Connection,
    expected_version: int | None = None,
) -> None:
    """Assert SQLite integrity, required tables and the schema version."""
    result = conn.execute("PRAGMA integrity_check").fetchone()
    assert result is not None and str(result[0]).lower() == "ok"

    ok, missing = migrations.validate_schema(conn)
    assert ok, f"missing tables: {missing}"

    version = migrations.get_current_version(conn)
    if expected_version is not None:
        assert version == expected_version
    else:
        latest = max(migrations.MIGRATIONS, default=0)
        assert version >= latest
