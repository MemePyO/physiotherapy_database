"""Tests for database indexes and schema migrations."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db

# Indexes created by migration version 2 (data/migrations/schema.py).
EXPECTED_INDEXES = {
    "patients": [
        "idx_patients_lower_name",
        "idx_patients_localitate",
        "idx_patients_updated_at",
        "idx_patients_created_at",
    ],
    "attachments": ["idx_attachments_patient"],
    "patient_history": ["idx_patient_history_patient"],
    "treatment_plans": ["idx_treatment_plans_patient"],
    "sessions": ["idx_sessions_patient_date"],
    "appointments": ["idx_appointments_datetime"],
    "outcome_measures": ["idx_outcome_measures_patient_date"],
    "exercises": ["idx_exercises_patient"],
}


def _fresh_db(monkeypatch):
    folder = tempfile.mkdtemp()
    dbfile = os.path.join(folder, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    return dbfile


def _index_names(dbfile, table):
    import sqlite3

    conn = sqlite3.connect(dbfile)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?", (table,)
        ).fetchall()
    finally:
        conn.close()
    return {r[0] for r in rows}


def test_indexes_created_on_fresh_db(monkeypatch):
    dbfile = _fresh_db(monkeypatch)
    for table, indexes in EXPECTED_INDEXES.items():
        present = _index_names(dbfile, table)
        for idx in indexes:
            assert idx in present, f"{idx} missing on {table}: {present}"


def test_schema_version_stamped(monkeypatch):
    _fresh_db(monkeypatch)
    assert db.get_schema_version() >= db.SCHEMA_VERSION


def test_init_db_is_idempotent(monkeypatch):
    dbfile = _fresh_db(monkeypatch)
    # Second run must not fail and must keep the indexes.
    db.init_db()
    for table, indexes in EXPECTED_INDEXES.items():
        present = _index_names(dbfile, table)
        for idx in indexes:
            assert idx in present


def test_existing_db_at_version_1_gets_migrated(monkeypatch):
    """Simulate a pre-index database stamped at version 1."""
    dbfile = _fresh_db(monkeypatch)

    import sqlite3

    conn = sqlite3.connect(dbfile)
    try:
        for table, indexes in EXPECTED_INDEXES.items():
            for idx in indexes:
                conn.execute(f"DROP INDEX IF EXISTS {idx}")
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
    finally:
        conn.close()

    assert "idx_appointments_datetime" not in _index_names(dbfile, "appointments")

    db.init_db()

    for table, indexes in EXPECTED_INDEXES.items():
        present = _index_names(dbfile, table)
        for idx in indexes:
            assert idx in present, f"{idx} missing after migration on {table}"
    assert db.get_schema_version() >= 2
