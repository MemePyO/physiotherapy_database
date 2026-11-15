"""Tests for the extended service layer."""

import os

import db
from services.appointment_service import AppointmentService
from services.attachment_service import AttachmentService
from services.database_service import DatabaseService
from services.history_service import HistoryService
from services.patient_service import PatientService
from services.physio_service import PhysioService


def _patient(name="Ana Test"):
    return db.add_patient(name)


# --- database service ----------------------------------------------------


def test_database_service_path_and_init(fresh_db):
    svc = DatabaseService()
    assert svc.path() == fresh_db
    assert os.path.exists(svc.path())
    assert svc.check_integrity() is True
    assert svc.schema_version() >= svc.expected_schema_version


def test_database_service_checkpoint(fresh_db):
    DatabaseService().checkpoint()


def test_database_service_connection(fresh_db):
    conn = DatabaseService().connection()
    try:
        assert conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0
    finally:
        conn.close()


# --- patient service -----------------------------------------------------


def test_patient_purge_and_empty_deleted(fresh_db):
    svc = PatientService()
    pid = svc.create_patient("Ana Test")[0]
    row_id = svc.delete_patient(pid)
    assert svc.list_deleted()

    assert svc.purge_deleted([row_id]) == 1
    assert svc.list_deleted() == []

    pid2 = svc.create_patient("Ion Test")[0]
    svc.delete_patient(pid2)
    assert len(svc.list_deleted()) == 1
    assert svc.empty_deleted() == 1
    assert svc.list_deleted() == []


def test_patient_restore(fresh_db):
    svc = PatientService()
    pid = svc.create_patient("Ana Test")[0]
    row_id = svc.delete_patient(pid)
    restored = svc.restore_patient(row_id)
    assert restored is not None
    assert svc.get_patient(patient_id=restored)["name"] == "Ana Test"


# --- physio service ------------------------------------------------------


def test_plan_upsert_and_get(fresh_db):
    pid = _patient()
    svc = PhysioService()
    assert svc.get_plan(pid) is None
    svc.upsert_plan(pid, diagnosis_code="M54.5", body_region="Lumbar", goals="Pain relief")
    plan = svc.get_plan(pid)
    assert plan["diagnosis_code"] == "M54.5"
    assert plan["body_region"] == "Lumbar"
    # second upsert updates in place
    svc.upsert_plan(pid, diagnosis_code="M54.6")
    plan2 = svc.get_plan(pid)
    assert plan2["id"] == plan["id"]
    assert plan2["diagnosis_code"] == "M54.6"


def test_session_crud(fresh_db):
    pid = _patient()
    svc = PhysioService()
    sid = svc.add_session(pid, date="01.02.2026", duration_min=45, pain_before=7, pain_after=4)
    rows = svc.list_sessions(pid)
    assert len(rows) == 1
    assert rows[0]["duration_min"] == 45
    svc.update_session(sid, pain_after=2)
    assert svc.list_sessions(pid)[0]["pain_after"] == 2
    svc.delete_session(sid)
    assert svc.list_sessions(pid) == []


def test_exercise_crud(fresh_db):
    pid = _patient()
    svc = PhysioService()
    eid = svc.add_exercise(pid, name="Bridging", sets=3, reps=10)
    rows = svc.list_exercises(pid)
    assert len(rows) == 1
    assert rows[0]["name"] == "Bridging"
    svc.update_exercise(eid, sets=4)
    assert svc.list_exercises(pid)[0]["sets"] == 4
    svc.delete_exercise(eid)
    assert svc.list_exercises(pid) == []


def test_outcome_crud(fresh_db):
    pid = _patient()
    svc = PhysioService()
    oid = svc.add_outcome(pid, measure="VAS", value=8, date="01.02.2026")
    rows = svc.list_outcomes(pid)
    assert len(rows) == 1
    assert rows[0]["value"] == 8
    svc.update_outcome(oid, value=5)
    assert svc.list_outcomes(pid)[0]["value"] == 5
    assert len(svc.list_outcomes(pid, measure="VAS")) == 1
    assert svc.list_outcomes(pid, measure="NRS") == []
    svc.delete_outcome(oid)
    assert svc.list_outcomes(pid) == []


# --- appointment service -------------------------------------------------


def test_appointment_crud(fresh_db):
    pid = _patient()
    svc = AppointmentService()
    aid = svc.add(pid, "01.02.2026 09:00", duration_min=30)
    all_rows = svc.list()
    assert len(all_rows) == 1
    assert all_rows[0]["patient_id"] == pid
    ranged = svc.list(start="01.02.2026 00:00", end="01.02.2026 23:59")
    assert len(ranged) == 1
    svc.update(aid, status="done")
    assert svc.list()[0]["status"] == "done"
    svc.delete(aid)
    assert svc.list() == []


# --- attachment service --------------------------------------------------


def test_attachment_crud(fresh_db, tmp_path):
    pid = _patient()
    svc = AttachmentService()
    f = tmp_path / "note.txt"
    f.write_text("hello")
    aid = svc.add(pid, str(f))
    rows = svc.list(pid)
    assert len(rows) == 1
    assert rows[0]["filename"] == "note.txt"
    assert svc.get(aid)["id"] == aid
    svc.delete(aid)
    assert svc.list(pid) == []


# --- history service -----------------------------------------------------


def test_history_add_list_clear(fresh_db):
    pid = _patient()
    svc = HistoryService()
    svc.add(pid, "diagnostic", "", "lower back pain")
    rows = svc.list(pid)
    assert len(rows) == 1
    assert rows[0]["field"] == "diagnostic"
    assert rows[0]["new_value"] == "lower back pain"
    svc.clear(pid)
    assert svc.list(pid) == []
