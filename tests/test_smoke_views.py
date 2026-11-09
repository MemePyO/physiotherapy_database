import os
import sys
import tempfile
import tkinter.messagebox as mb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
import main


def _fresh_app(monkeypatch, tmp_path):
    d = tempfile.mkdtemp()
    dbfile = os.path.join(d, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    pid = db.add_patient("Ana", "Cluj", sex="F", dob="01.02.1990")
    db.update_patient(
        pid, diagnostic="diag **bold**", objective="obj", evaluation="eva", observation="obs"
    )
    main.theme.set_theme("classic")
    main.theme.set_appearance("Light")
    monkeypatch.setattr(
        main,
        "load_settings",
        lambda: {"ui_theme": "classic", "appearance": "Light", "ui_scale": 1.0},
    )
    app = main.App()
    app.update()
    return app, pid


def _silent_messageboxes():
    mb.showinfo = lambda *a, **k: None
    mb.showerror = lambda *a, **k: None
    mb.askyesno = lambda *a, **k: True


def test_all_views_render(monkeypatch, tmp_path):
    _silent_messageboxes()
    app, pid = _fresh_app(monkeypatch, tmp_path)
    for v in ("patients", "trash", "settings", "saveas", "backup", "new"):
        app._show_view(v)
        app.update()
    app._show_view("patients")
    app.update()
    app.destroy()


def test_patient_panel_actions(monkeypatch, tmp_path):
    _silent_messageboxes()
    app, pid = _fresh_app(monkeypatch, tmp_path)
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]
    # toolbar actions
    for a_name in ("bold", "italic", "bullet", "number"):
        panel._toolbar_action("diagnostic", a_name)
    panel._on_text_change("diagnostic", panel.diagnostic_text)
    panel.mark_dirty()
    panel._save_all(silent=True)
    app.update()
    # attachments/history (classic)
    panel._load_attachments()
    panel._load_history()
    panel._update_count("diagnostic", panel.diagnostic_text)
    panel._refresh_header_info()
    # clear history
    panel._clear_history()
    app.update()
    app.destroy()


def test_medidash_views(monkeypatch, tmp_path):
    _silent_messageboxes()
    d = tempfile.mkdtemp()
    dbfile = os.path.join(d, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    db.add_patient("Bob", "Iasi")
    main.theme.set_theme("medidash")
    app = main.App()
    app.update()
    app._show_view("patients")
    app.update()
    pid = db.get_all_patients()[0]["id"]
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]
    panel.diagnostic_text.insert("1.0", "x")
    panel.mark_dirty()
    panel._save_all(silent=True)
    app.update()
    app._apply_ui_theme("classic")
    app.update()
    app.destroy()
    main.theme.set_theme("classic")
