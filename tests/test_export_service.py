"""Tests for services/export_service.py."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest.mock as m

import db
from services.export_service import export_csv, export_pdf, export_word


def _fresh_db(monkeypatch):
    folder = tempfile.mkdtemp()
    dbfile = os.path.join(folder, "test.db")
    m.patch.object(db, "db_path", lambda: dbfile).start()
    db.init_db()
    db.add_patient("Ana Test", "Cluj")
    db.add_patient("Ion Popescu", "Brasov")
    return folder


def test_export_csv(monkeypatch):
    folder = _fresh_db(monkeypatch)
    path = os.path.join(folder, "out.csv")
    n = export_csv(path)
    assert n == 2
    assert os.path.exists(path)
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    assert "Ana Test" in content
    assert "Ion Popescu" in content


def test_export_pdf(monkeypatch):
    folder = _fresh_db(monkeypatch)
    path = os.path.join(folder, "out.pdf")
    n = export_pdf(path)
    assert n == 2
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read(4) == b"%PDF"


def test_export_word(monkeypatch):
    folder = _fresh_db(monkeypatch)
    path = os.path.join(folder, "out.doc")
    n = export_word(path)
    assert n == 2
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "Ana Test" in content
