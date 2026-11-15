"""Additional coverage for database maintenance and helper paths."""

import json
import os

import db


def test_backup_to_and_verify(fresh_db, tmp_path):
    db.add_patient("Ana")
    dest = os.path.join(tmp_path, "backup.db")
    assert db.backup_to(dest) is True
    ok, count = db.verify_backup(dest)
    assert ok is True
    assert count == 1

    broken = os.path.join(tmp_path, "broken.db")
    with open(broken, "wb") as fh:
        fh.write(b"not a database")
    ok, reason = db.verify_backup(broken)
    assert ok is False
    assert reason


def test_backup_to_missing_folder_is_created(fresh_db, tmp_path):
    dest = os.path.join(tmp_path, "nested", "dir", "backup.db")
    assert db.backup_to(dest) is True
    assert os.path.exists(dest)


def test_pre_operation_backup_writes_file(fresh_db, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_data_dir", lambda: str(tmp_path))
    db.add_patient("Ana")
    db.pre_operation_backup("test")
    files = os.listdir(os.path.join(tmp_path, "backup"))
    assert any(name.startswith("pre_test_") for name in files)


def test_pre_migration_backup_returns_none_for_missing_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "db_path", lambda: os.path.join(tmp_path, "missing.db"))
    assert db.pre_migration_backup() is None


def test_pre_migration_backup_creates_file(fresh_db):
    path = db.pre_migration_backup()
    assert path is not None
    assert os.path.exists(path)


def test_checkpoint_is_safe(fresh_db):
    db.checkpoint()


def test_migrate_from_json(tmp_path, monkeypatch, fresh_db):
    monkeypatch.setattr(db, "_base_dir", lambda: str(tmp_path))
    json_path = os.path.join(tmp_path, "patients.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(["Ion", "  Ana  ", "", 3], fh)

    conn = db._get_conn()
    try:
        db.migrate_from_json(conn)
    finally:
        conn.close()

    names = {p["name"] for p in db.get_all_patients()}
    assert {"Ion", "Ana", "3"} <= names
    assert not os.path.exists(json_path)
    assert os.path.exists(json_path + ".migrated")


def test_field_helpers(fresh_db):
    pid = db.add_patient("Ana")
    db.update_patient(
        pid,
        diagnostic="diag",
        objective="obj",
        evaluation="eva",
        observation="obs",
    )
    assert db.get_diagnostic(pid) == "diag"
    assert db.get_objective(pid) == "obj"
    assert db.get_evaluation(pid) == "eva"
    assert db.get_observation(pid) == "obs"
    # missing patient yields empty strings
    assert db.get_diagnostic(9999) == ""


def test_get_patient_by_name(fresh_db):
    pid = db.add_patient("Ana Pop")
    assert db.get_patient(name="Ana Pop")["id"] == pid
    assert db.get_patient(name="Nobody") is None


def test_attachment_missing_paths(fresh_db):
    assert db.get_attachment(9999) is None
    # deleting a non-existent attachment must not raise
    db.delete_attachment(9999)


def test_attachment_rejects_missing_file(fresh_db):
    try:
        db.add_attachment(1, "does-not-exist.txt")
        raised = False
    except ValueError:
        raised = True
    assert raised
