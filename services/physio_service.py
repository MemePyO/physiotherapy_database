"""Physiotherapy domain service.

Business operations for treatment plans, therapy sessions, home exercise
programmes and outcome measures (VAS/NRS).  The UI talks to this service;
the service talks to the ``db`` repository.
"""

import db

# Re-exported so UI code does not need to import the repository for constants.
SESSION_STATUSES = list(db.SESSION_STATUSES)
OUTCOME_MEASURES = list(db.OUTCOME_MEASURES)
BODY_REGIONS = list(db.BODY_REGIONS)
SIDES = list(db.SIDES)


class PhysioService:
    """Plans, sessions, exercises and outcome measures."""

    # --- treatment plans -------------------------------------------------
    def get_plan(self, patient_id):
        return db.get_plan(patient_id)

    def upsert_plan(self, patient_id, **fields):
        return db.upsert_plan(patient_id, **fields)

    # --- sessions --------------------------------------------------------
    def list_sessions(self, patient_id):
        return db.list_sessions(patient_id)

    def add_session(self, patient_id, **fields):
        return db.add_session(patient_id, **fields)

    def update_session(self, session_id, **fields):
        db.update_session(session_id, **fields)

    def delete_session(self, session_id):
        db.delete_session(session_id)

    # --- exercises -------------------------------------------------------
    def list_exercises(self, patient_id):
        return db.list_exercises(patient_id)

    def add_exercise(self, patient_id, **fields):
        return db.add_exercise(patient_id, **fields)

    def update_exercise(self, exercise_id, **fields):
        db.update_exercise(exercise_id, **fields)

    def delete_exercise(self, exercise_id):
        db.delete_exercise(exercise_id)

    # --- outcome measures ------------------------------------------------
    def list_outcomes(self, patient_id, measure=None):
        return db.list_outcomes(patient_id, measure=measure)

    def add_outcome(self, patient_id, measure, value, date, notes=""):
        return db.add_outcome(patient_id, measure, value, date, notes=notes)

    def update_outcome(self, outcome_id, **fields):
        db.update_outcome(outcome_id, **fields)

    def delete_outcome(self, outcome_id):
        db.delete_outcome(outcome_id)


_service = None


def get_physio_service() -> PhysioService:
    global _service
    if _service is None:
        _service = PhysioService()
    return _service
