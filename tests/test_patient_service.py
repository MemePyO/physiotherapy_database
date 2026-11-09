"""Tests for services/patient_service.py."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest.mock as m
import db
from services.patient_service import PatientService, get_patient_service


def _fresh_db(monkeypatch):
    folder = tempfile.mkdtemp()
    dbfile = os.path.join(folder, "test.db")
    m.patch.object(db, "db_path", lambda: dbfile).start()
    db.init_db()
    return folder, dbfile


def test_create_and_get_patient(monkeypatch):
    _fresh_db(monkeypatch)
    svc = PatientService()
    pid, validation = svc.create_patient("Ana Test", "Cluj", sex="F", dob="01.02.1990")
    assert validation.ok()
    assert pid is not None
    p = svc.get_patient(patient_id=pid)
    assert p["name"] == "Ana Test"


def test_create_patient_empty_name_fails(monkeypatch):
    _fresh_db(monkeypatch)
    svc = PatientService()
    pid, validation = svc.create_patient("")
    assert not validation.ok()
    assert pid is None


def test_create_patient_invalid_dob_fails(monkeypatch):
    _fresh_db(monkeypatch)
    svc = PatientService()
    pid, validation = svc.create_patient("Ana", dob="bad")
    assert not validation.ok()
    assert pid is None


def test_update_patient(monkeypatch):
    _fresh_db(monkeypatch)
    svc = PatientService()
    pid, _ = svc.create_patient("Ana Test", "Cluj")
    err = svc.update_patient(pid, localitate="Bucuresti", diagnostic="diag")
    assert err is None
    p = svc.get_patient(patient_id=pid)
    assert p["localitate"] == "Bucuresti"
    assert p["diagnostic"] == "diag"


def test_update_patient_invalid_name(monkeypatch):
    _fresh_db(monkeypatch)
    svc = PatientService()
    pid, _ = svc.create_patient("Ana Test", "Cluj")
    err = svc.update_patient(pid, name="")
    assert err is not None
    assert not err.ok()


def test_delete_and_restore(monkeypatch):
    _fresh_db(monkeypatch)
    svc = PatientService()
    pid, _ = svc.create_patient("Ana Test", "Cluj")
    deleted_row_id = svc.delete_patient(pid)
    assert deleted_row_id is not None
    deleted = svc.list_deleted()
    assert any(d["id"] == deleted_row_id for d in deleted)
    restored_pid = svc.restore_patient(deleted_row_id)
    assert restored_pid is not None


def test_list_patients_with_query(monkeypatch):
    _fresh_db(monkeypatch)
    svc = PatientService()
    svc.create_patient("Ana Test", "Cluj")
    svc.create_patient("Ion Popescu", "Brasov")
    results = svc.list_patients(query="ana")
    assert len(results) == 1
    assert results[0]["name"] == "Ana Test"

    all_results = svc.list_patients()
    assert len(all_results) == 2


def test_ensure_patient_exists(monkeypatch):
    _fresh_db(monkeypatch)
    svc = PatientService()
    pid = svc.ensure_patient_exists("New Patient")
    assert pid is not None
    # calling again returns same id
    pid2 = svc.ensure_patient_exists("New Patient")
    assert pid == pid2


def test_get_patient_service_singleton():
    svc1 = get_patient_service()
    svc2 = get_patient_service()
    assert svc1 is svc2