"""Tests for services/backup_service.py."""

import os

import db
from services.backup_service import BackupService, get_backup_service


def test_backup_verify_and_pre_operation(fresh_db, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_data_dir", lambda: str(tmp_path))
    db.add_patient("Ana")
    svc = BackupService()

    dest = os.path.join(tmp_path, "backup.db")
    assert svc.backup_to(dest) is True
    ok, count = svc.verify(dest)
    assert ok is True
    assert count == 1

    svc.checkpoint()
    svc.pre_operation("test")
    backups = os.listdir(os.path.join(tmp_path, "backup"))
    assert any(name.startswith("pre_test_") for name in backups)


def test_restore_from_replaces_database(fresh_db, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_data_dir", lambda: str(tmp_path))
    db.add_patient("Ana")
    svc = BackupService()
    dest = os.path.join(tmp_path, "snapshot.db")
    assert svc.backup_to(dest) is True

    db.add_patient("Ion")
    assert {p["name"] for p in db.get_all_patients()} == {"Ana", "Ion"}

    svc.restore_from(dest)
    assert [p["name"] for p in db.get_all_patients()] == ["Ana"]


def test_backup_service_singleton():
    assert get_backup_service() is get_backup_service()
