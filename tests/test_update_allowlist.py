"""Tests for the UPDATE column allowlists.

Dynamic ``UPDATE ... SET`` statements build their column list from constants in
``db``.  These tests make sure those constants never drift from the schema and
that unknown keyword arguments are silently ignored rather than interpolated
into SQL.
"""

import sqlite3

import db

ALLOWLISTS = {
    "patients": db.PATIENT_UPDATE_COLUMNS,
    "treatment_plans": db.PLAN_UPDATE_COLUMNS,
    "sessions": db.SESSION_UPDATE_COLUMNS,
    "appointments": db.APPOINTMENT_UPDATE_COLUMNS,
    "outcome_measures": db.OUTCOME_UPDATE_COLUMNS,
    "exercises": db.EXERCISE_UPDATE_COLUMNS,
}


def _table_columns(dbfile, table):
    conn = sqlite3.connect(dbfile)
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def test_allowlists_only_reference_real_columns(fresh_db):
    for table, columns in ALLOWLISTS.items():
        schema = _table_columns(fresh_db, table)
        missing = set(columns) - schema
        assert not missing, f"{table} allowlist references unknown columns: {missing}"


def test_update_clause_ignores_unknown_columns():
    assignments, params = db._update_clause(
        ("a", "b"), {"a": 1, "b": 2, "c": 3, "1 = 1; DROP TABLE patients": 4}
    )
    assert assignments == ["a = ?", "b = ?"]
    assert params == [1, 2]


def test_update_clause_skips_none_values():
    assignments, params = db._update_clause(("a", "b"), {"a": None, "b": 2})
    assert assignments == ["b = ?"]
    assert params == [2]


def test_update_session_ignores_unknown_field(fresh_db):
    pid = db.add_patient("Ana")
    sid = db.add_session(pid, date="01.02.2026")
    db.update_session(sid, status="done", **{"notes = 'x'": "ignored"})
    row = db.list_sessions(pid)[0]
    assert row["status"] == "done"
    assert row["id"] == sid


def test_update_patient_only_allowed_columns(fresh_db):
    pid = db.add_patient("Ana")
    db.update_patient(pid, diagnostic="diag")
    assert db.get_patient(patient_id=pid)["diagnostic"] == "diag"
    # The internals build the SET list from the allowlist, not from the dict.
    assert "id" not in db.PATIENT_UPDATE_COLUMNS
    assert "created_at" not in db.PATIENT_UPDATE_COLUMNS
