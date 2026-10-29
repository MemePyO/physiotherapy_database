import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


def _fresh_db(monkeypatch):
    d = tempfile.mkdtemp()
    dbfile = os.path.join(d, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    return dbfile


def test_add_and_get(monkeypatch):
    _fresh_db(monkeypatch)
    pid = db.add_patient("Ion Popescu", "Cluj", sex="M", dob="01.02.1990")
    assert isinstance(pid, int)
    p = db.get_patient(patient_id=pid)
    assert p["name"] == "Ion Popescu"
    assert p["localitate"] == "Cluj"
    assert p["sex"] == "M"
    assert p["dob"] == "01.02.1990"
    assert p["patient_code"].startswith("PP-")


def test_duplicate_name_raises(monkeypatch):
    _fresh_db(monkeypatch)
    db.add_patient("Ana")
    try:
        db.add_patient("Ana")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_update_patient(monkeypatch):
    _fresh_db(monkeypatch)
    pid = db.add_patient("Ana")
    db.update_patient(pid, diagnostic="diag1", localitate="Buc")
    p = db.get_patient(patient_id=pid)
    assert p["diagnostic"] == "diag1"
    assert p["localitate"] == "Buc"


def test_history_recorded(monkeypatch):
    _fresh_db(monkeypatch)
    pid = db.add_patient("Ana")
    db.update_patient(pid, diagnostic="diag1")
    hist = db.list_history(pid)
    assert any(h["field"] == "diagnostic" for h in hist)


def test_soft_delete_and_restore(monkeypatch):
    _fresh_db(monkeypatch)
    pid = db.add_patient("Ana")
    db.delete_patient(pid)
    assert db.get_patient(patient_id=pid) is None
    deleted = db.list_deleted()
    assert any(d["name"] == "Ana" for d in deleted)
    row_id = deleted[0]["id"]
    new_pid = db.restore_deleted(row_id)
    assert new_pid is not None
    assert db.get_patient(patient_id=new_pid) is not None


def test_get_all_patients(monkeypatch):
    _fresh_db(monkeypatch)
    db.add_patient("B")
    db.add_patient("A")
    names = [p["name"] for p in db.get_all_patients()]
    assert names == sorted(names)


def test_attachments(monkeypatch, tmp_path):
    _fresh_db(monkeypatch)
    pid = db.add_patient("Ana")
    f = tmp_path / "x.txt"
    f.write_text("hi")
    aid = db.add_attachment(pid, str(f))
    assert aid is not None
    atts = db.list_attachments(pid)
    assert len(atts) == 1
    assert atts[0]["filename"] == "x.txt"
    db.delete_attachment(aid)
    assert db.list_attachments(pid) == []


def test_localities(monkeypatch):
    _fresh_db(monkeypatch)
    db.add_patient("A", localitate="Cluj")
    db.add_patient("B", localitate="Cluj")
    assert "Cluj" in db.get_localities()
