"""Concrete schema migrations.

Each migration is a callable that receives an open SQLite connection and
applies a small, idempotent schema change.  Migrations are registered with
``data.migrations.register`` and executed in version order by
``data.migrations.run_migrations``.
"""

from . import register

# (index_name, create_statement)
# Indexes are created with IF NOT EXISTS so a migration can be retried safely.
INDEX_STATEMENTS = [
    (
        "idx_patients_lower_name",
        "CREATE INDEX IF NOT EXISTS idx_patients_lower_name ON patients (LOWER(name))",
    ),
    (
        "idx_patients_localitate",
        "CREATE INDEX IF NOT EXISTS idx_patients_localitate ON patients (localitate)",
    ),
    (
        "idx_patients_updated_at",
        "CREATE INDEX IF NOT EXISTS idx_patients_updated_at ON patients (updated_at)",
    ),
    (
        "idx_patients_created_at",
        "CREATE INDEX IF NOT EXISTS idx_patients_created_at ON patients (created_at)",
    ),
    (
        "idx_attachments_patient",
        "CREATE INDEX IF NOT EXISTS idx_attachments_patient ON attachments (patient_id)",
    ),
    (
        "idx_patient_history_patient",
        "CREATE INDEX IF NOT EXISTS idx_patient_history_patient "
        "ON patient_history (patient_id, id DESC)",
    ),
    (
        "idx_treatment_plans_patient",
        "CREATE INDEX IF NOT EXISTS idx_treatment_plans_patient ON treatment_plans (patient_id)",
    ),
    (
        "idx_sessions_patient_date",
        "CREATE INDEX IF NOT EXISTS idx_sessions_patient_date "
        "ON sessions (patient_id, date DESC, id DESC)",
    ),
    (
        "idx_appointments_datetime",
        "CREATE INDEX IF NOT EXISTS idx_appointments_datetime ON appointments (datetime)",
    ),
    (
        "idx_outcome_measures_patient_date",
        "CREATE INDEX IF NOT EXISTS idx_outcome_measures_patient_date "
        "ON outcome_measures (patient_id, date)",
    ),
    (
        "idx_exercises_patient",
        "CREATE INDEX IF NOT EXISTS idx_exercises_patient ON exercises (patient_id)",
    ),
]


def create_indexes(conn):
    """Create all performance indexes (idempotent)."""
    cur = conn.cursor()
    for _name, statement in INDEX_STATEMENTS:
        cur.execute(statement)
    conn.commit()


register(2, "add performance indexes", create_indexes)
