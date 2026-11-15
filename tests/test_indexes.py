"""Tests for database indexes and schema migrations."""

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


def test_indexes_created_on_fresh_db(fresh_db):
    for table, indexes in EXPECTED_INDEXES.items():
        present = _index_names(fresh_db, table)
        for idx in indexes:
            assert idx in present, f"{idx} missing on {table}: {present}"


def test_schema_version_stamped(fresh_db):
    assert db.get_schema_version() >= db.SCHEMA_VERSION


def test_init_db_is_idempotent(fresh_db):
    # Second run must not fail and must keep the indexes.
    db.init_db()
    for table, indexes in EXPECTED_INDEXES.items():
        present = _index_names(fresh_db, table)
        for idx in indexes:
            assert idx in present


def test_existing_db_at_version_1_gets_migrated(fresh_db):
    """Simulate a pre-index database stamped at version 1."""
    import sqlite3

    conn = sqlite3.connect(fresh_db)
    try:
        for table, indexes in EXPECTED_INDEXES.items():
            for idx in indexes:
                conn.execute(f"DROP INDEX IF EXISTS {idx}")
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
    finally:
        conn.close()

    assert "idx_appointments_datetime" not in _index_names(fresh_db, "appointments")

    db.init_db()

    for table, indexes in EXPECTED_INDEXES.items():
        present = _index_names(fresh_db, table)
        for idx in indexes:
            assert idx in present, f"{idx} missing after migration on {table}"
    assert db.get_schema_version() >= 2
