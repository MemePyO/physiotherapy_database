"""Tests for services/export_service.py."""

import os

import db
from services.export_service import export_csv, export_pdf, export_word


def _seed():
    db.add_patient("Ana Test", "Cluj")
    db.add_patient("Ion Popescu", "Brasov")


def test_export_csv(fresh_db, tmp_path):
    _seed()
    path = os.path.join(tmp_path, "out.csv")
    n = export_csv(path)
    assert n == 2
    assert os.path.exists(path)
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    assert "Ana Test" in content
    assert "Ion Popescu" in content


def test_export_pdf(fresh_db, tmp_path):
    _seed()
    path = os.path.join(tmp_path, "out.pdf")
    n = export_pdf(path)
    assert n == 2
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read(4) == b"%PDF"


def test_export_word(fresh_db, tmp_path):
    _seed()
    path = os.path.join(tmp_path, "out.doc")
    n = export_word(path)
    assert n == 2
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "Ana Test" in content
