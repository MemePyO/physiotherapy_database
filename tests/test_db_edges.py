"""Edge-case coverage for db.py validation and maintenance paths."""

import pytest

import db


def test_add_patient_rejects_invalid_names(fresh_db):
    for bad in ("", "   "):
        with pytest.raises(ValueError):
            db.add_patient(bad)
    with pytest.raises(ValueError):
        db.add_patient("x" * (db.MAX_NAME_LEN + 1))


def test_update_patient_validation(fresh_db):
    pid = db.add_patient("Ana")
    # no fields is a silent no-op
    db.update_patient(pid)

    with pytest.raises(ValueError):
        db.update_patient(pid, name="")
    with pytest.raises(ValueError):
        db.update_patient(pid, name="x" * (db.MAX_NAME_LEN + 1))
    with pytest.raises(ValueError):
        db.update_patient(pid, localitate="x" * (db.MAX_LOCALITY_LEN + 1))
    with pytest.raises(ValueError):
        db.update_patient(pid, diagnostic="x" * (db.MAX_TEXT_LEN + 1))

    db.update_patient(pid, nr_zile="10", decision_date="01.01.2026")
    row = db.get_patient(patient_id=pid)
    assert row["nr_zile"] == "10"
    assert row["decision_date"] == "01.01.2026"


def test_update_patient_duplicate_name_raises(fresh_db):
    db.add_patient("Ana")
    bob = db.add_patient("Bob")
    with pytest.raises(ValueError):
        db.update_patient(bob, name="Ana")


def test_get_patient_without_lookup_key(fresh_db):
    assert db.get_patient() is None


def test_delete_and_restore_missing_rows(fresh_db):
    assert db.delete_patient(9999) is None
    assert db.restore_deleted(9999) is None


def test_purge_deleted_empty_input(fresh_db):
    assert db.purge_deleted([]) == 0
    assert db.purge_deleted(None) == 0


def test_ensure_patient_exists_empty_name(fresh_db):
    assert db.ensure_patient_exists("") is None
    assert db.ensure_patient_exists("   ") is None


def test_attachment_duplicate_name_gets_suffix(fresh_db, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_data_dir", lambda: str(tmp_path))
    pid = db.add_patient("Ana")
    src = tmp_path / "note.txt"
    src.write_text("one")
    a1 = db.add_attachment(pid, str(src))
    a2 = db.add_attachment(pid, str(src))
    assert a1 != a2
    names = [a["filename"] for a in db.list_attachments(pid)]
    assert "note.txt" in names
    assert "note_1.txt" in names


def test_attachment_too_large(fresh_db, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_data_dir", lambda: str(tmp_path))
    src = tmp_path / "big.bin"
    src.write_bytes(b"x")
    monkeypatch.setattr(db.os.path, "getsize", lambda path: 51 * 1024 * 1024)
    with pytest.raises(ValueError):
        db.add_attachment(1, str(src))


def test_update_crud_noops_with_no_fields(fresh_db):
    # Each update helper returns quietly when no allowlisted field is supplied.
    db.update_session(9999)
    db.update_appointment(9999)
    db.update_outcome(9999)
    db.update_exercise(9999)


def test_pre_migration_backup_failure_returns_none(fresh_db, monkeypatch):
    monkeypatch.setattr(db, "backup_to", lambda dest: False)
    assert db.pre_migration_backup() is None
