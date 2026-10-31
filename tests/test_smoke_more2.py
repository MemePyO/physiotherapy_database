import sys, os, tempfile, tkinter.messagebox as mb, tkinter.filedialog as fd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
import main


def _fresh_app(monkeypatch, tmp_path, theme="classic"):
    d = tempfile.mkdtemp()
    dbfile = os.path.join(d, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    pid = db.add_patient("Ana", "Cluj", sex="F", dob="01.02.1990")
    db.update_patient(pid, diagnostic="diag", objective="obj", evaluation="eva", observation="obs")
    main.theme.set_theme(theme)
    app = main.App()
    app.update()
    return app, pid


def _silent(monkeypatch, tmp_path):
    mb.showinfo = lambda *a, **k: None
    mb.showerror = lambda *a, **k: None
    mb.askyesno = lambda *a, **k: True
    fd.asksaveasfilename = lambda **kw: os.path.join(tempfile.mkdtemp(), "out")
    fd.askopenfilename = lambda **kw: ""
    monkeypatch.setattr(main.App, "wait_window", lambda self, w: None)


def test_more_main_paths2(monkeypatch, tmp_path):
    _silent(monkeypatch, tmp_path)
    app, pid = _fresh_app(monkeypatch, tmp_path)
    app.selected_patient_id = pid
    # theme + scale + language
    app._toggle_theme()
    app._set_ui_scale(1.25)
    app._on_language_change("English")
    # clear search (classic has entry)
    app.search_entry.insert(0, "x")
    app._clear_search()
    app._navigate_patient(1)
    app._navigate_patient(-1)
    # backup
    app._backup_now()
    # trash dialog interactions
    app._show_view("trash")
    app.update()
    app._show_view("patients")
    app.update()
    # new patient inline cancel
    app._open_patient_by_id(None)
    app.update()
    panel = app.patient_panels.get(None)
    panel._cancel_new()
    app.update()
    # settings dialog
    from dialogs import SettingsDialog
    dlg = SettingsDialog(app)
    app.update()
    dlg.destroy()
    app.destroy()


def test_more_panel_paths(monkeypatch, tmp_path):
    _silent(monkeypatch, tmp_path)
    app, pid = _fresh_app(monkeypatch, tmp_path)
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]
    # print pdf (filedialog returns "" -> no-op)
    panel._print_pdf()
    # autosave
    panel._auto_save()
    # _on_text_change
    panel._on_text_change("diagnostic", panel.diagnostic_text)
    # cancel new not applicable
    app.destroy()