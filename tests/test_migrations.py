"""Migration upgrade, rollback and future-schema validation."""

import sqlite3

import pytest
from migration_helpers import (
    assert_schema_integrity,
    column_names,
    downgrade_database,
    index_names,
    table_names,
    temporary_migrations,
)

import data.migrations as migrations
import db
from data.migrations.schema import INDEX_STATEMENTS


@pytest.fixture
def legacy_db(fresh_db):
    """A database that looks like a pre-index (version 1) installation."""
    downgrade_database(fresh_db, version=1)
    return fresh_db


def _connect(dbfile):
    return sqlite3.connect(dbfile)


def test_upgrade_from_version_1_applies_pending_migrations(legacy_db):
    conn = _connect(legacy_db)
    try:
        assert migrations.get_current_version(conn) == 1
        assert index_names(conn, "appointments") == set()

        applied = migrations.run_migrations(conn)

        assert applied == sorted(applied)
        assert 2 in applied
        assert migrations.get_current_version(conn) >= 2
        assert_schema_integrity(conn)
        for index_name, _statement in INDEX_STATEMENTS:
            assert index_name in index_names(conn)
    finally:
        conn.close()


def test_running_migrations_twice_is_idempotent(legacy_db):
    conn = _connect(legacy_db)
    try:
        first = migrations.run_migrations(conn)
        assert first

        second = migrations.run_migrations(conn)

        assert second == []
        assert_schema_integrity(conn)
    finally:
        conn.close()


def test_failed_migration_rolls_back_schema_and_version(legacy_db):
    def broken(conn):
        conn.execute("CREATE TABLE migration_probe (id INTEGER)")
        raise RuntimeError("boom")

    latest = max(migrations.MIGRATIONS, default=0)
    with temporary_migrations([(latest + 10, "broken probe", broken)]):
        conn = _connect(legacy_db)
        try:
            with pytest.raises(RuntimeError, match="boom"):
                migrations.run_migrations(conn)

            assert migrations.get_current_version(conn) == latest
            assert "migration_probe" not in table_names(conn)
            assert_schema_integrity(conn, expected_version=latest)
        finally:
            conn.close()


def test_failed_migration_can_be_retried_with_a_fixed_version(legacy_db):
    latest = max(migrations.MIGRATIONS, default=0)
    version = latest + 10

    def broken(conn):
        raise RuntimeError("boom")

    def fixed(conn):
        conn.execute("CREATE TABLE migration_probe (id INTEGER)")

    with temporary_migrations([(version, "broken probe", broken)]):
        conn = _connect(legacy_db)
        try:
            with pytest.raises(RuntimeError):
                migrations.run_migrations(conn)
        finally:
            conn.close()

    with temporary_migrations([(version, "fixed probe", fixed)]):
        conn = _connect(legacy_db)
        try:
            applied = migrations.run_migrations(conn)

            assert version in applied
            assert "migration_probe" in table_names(conn)
            assert_schema_integrity(conn, expected_version=version)
        finally:
            conn.close()


def test_registered_migrations_are_well_formed():
    assert migrations.MIGRATIONS

    for version, (description, fn) in migrations.MIGRATIONS.items():
        assert isinstance(version, int) and version > 0
        assert isinstance(description, str) and description.strip()
        assert callable(fn)

    versions = list(migrations.MIGRATIONS)
    assert versions == sorted(versions)


def test_future_migration_applies_to_the_current_schema(legacy_db):
    latest = max(migrations.MIGRATIONS, default=0)
    version = latest + 10

    def add_probe_column(conn):
        conn.execute("ALTER TABLE patients ADD COLUMN migration_probe TEXT DEFAULT ''")

    with temporary_migrations([(version, "add probe column", add_probe_column)]):
        conn = _connect(legacy_db)
        try:
            applied = migrations.run_migrations(conn)

            assert version in applied
            assert "migration_probe" in column_names(conn, "patients")
            assert_schema_integrity(conn, expected_version=version)
        finally:
            conn.close()


def test_validate_schema_reports_missing_tables(legacy_db):
    conn = _connect(legacy_db)
    try:
        ok, missing = migrations.validate_schema(conn, expected_tables=["patients", "nope"])
        assert ok is False
        assert missing == ["nope"]
    finally:
        conn.close()


def test_schema_version_survives_reinitialisation(fresh_db):
    assert db.get_schema_version() >= db.SCHEMA_VERSION

    db.init_db()

    assert db.get_schema_version() >= db.SCHEMA_VERSION
    conn = _connect(fresh_db)
    try:
        assert_schema_integrity(conn)
    finally:
        conn.close()
