"""Shared pytest fixtures.

Centralises the temporary-database setup and the dialog stubs that were
previously duplicated in every test module.
"""

import gc
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402


def pytest_configure(config):
    """Stabilise repeated root-window creation on Windows.

    CustomTkinter's title-bar colour code calls ``Tk.update()`` from inside
    ``CTk.__init__``.  Creating and destroying many roots in one pytest process
    (one per UI test) can crash Tcl/Tk with an access violation.  Title-bar
    colouring is purely cosmetic, so tests disable that one hook.
    """
    import customtkinter as ctk

    ctk.CTk._deactivate_windows_window_header_manipulation = True


@pytest.fixture
def fresh_db(monkeypatch):
    """Point ``db`` at a fresh temporary database and initialise the schema."""
    import tempfile

    folder = tempfile.mkdtemp()
    dbfile = os.path.join(folder, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    return dbfile


@pytest.fixture
def seeded_db(fresh_db):
    """A fresh database with one fully populated patient; returns the id."""
    pid = db.add_patient("Ana Test", "Cluj", sex="F", dob="01.02.1990")
    db.update_patient(
        pid,
        diagnostic="diag",
        objective="obj",
        evaluation="eva",
        observation="obs",
    )
    return pid


@pytest.fixture
def silent_dialogs(monkeypatch):
    """Make message boxes and file dialogs no-ops for unattended tests."""
    from tkinter import filedialog, messagebox

    monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: None)
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: "")
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kw: "")
    return None


@pytest.fixture
def app(fresh_db, silent_dialogs, monkeypatch):
    """Build the real App against the temporary database, then tear it down."""
    import main

    main.theme.set_theme("classic")
    main.theme.set_appearance("Light")
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: {"ui_theme": "classic", "appearance": "Light", "ui_scale": 1.0},
    )
    instance = main.App()
    instance.update()
    yield instance
    try:
        instance.update_idletasks()
    except Exception:
        pass
    try:
        instance.destroy()
    except Exception:
        pass
    gc.collect()


@pytest.fixture
def patient_app(seeded_db, app):
    """The App plus the id of the seeded patient."""
    return app, seeded_db
