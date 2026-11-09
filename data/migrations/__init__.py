"""Migration framework for database schema versioning."""

import logging

logger = logging.getLogger(__name__)

MIGRATIONS = {}  # version -> (description, callable)


def register(version, description, fn):
    MIGRATIONS[version] = (description, fn)


def get_current_version(conn):
    try:
        return int(conn.execute("PRAGMA user_version").fetchone()[0] or 0)
    except Exception:
        return 0


def set_version(conn, version):
    conn.execute(f"PRAGMA user_version = {version}")
    conn.commit()


def run_migrations(conn, target_version=None):
    """Run all pending migrations up to target_version."""
    current = get_current_version(conn)
    if target_version is None:
        target_version = max(MIGRATIONS.keys()) if MIGRATIONS else current
    applied = []
    for v in sorted(MIGRATIONS.keys()):
        if v <= current:
            continue
        if v > target_version:
            break
        desc, fn = MIGRATIONS[v]
        try:
            logger.info("Applying migration %d: %s", v, desc)
            fn(conn)
            set_version(conn, v)
            applied.append(v)
        except Exception as e:
            logger.error("Migration %d failed: %s", v, e)
            raise
    return applied


def validate_schema(conn, expected_tables=None):
    """Check that all expected tables exist."""
    if expected_tables is None:
        expected_tables = [
            "patients",
            "deleted_patients",
            "treatment_plans",
            "sessions",
            "appointments",
            "outcome_measures",
            "exercises",
            "patient_history",
            "attachments",
        ]
    existing = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    missing = [t for t in expected_tables if t not in existing]
    return len(missing) == 0, missing
