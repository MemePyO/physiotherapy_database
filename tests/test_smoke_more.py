import sys, os, tempfile, tkinter.messagebox as mb, tkinter.filedialog as fd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
import main


def _fresh_app(monkeypatch, tmp_path):
    d = tempfile.mkdtemp()
    dbfile = os.path.join(d, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    pid = db.add_patient("Ana", "Cluj", sex="F", dob="01.02.1990")
    db.update_patient(pid, diagnostic="diag", objective="obj", evaluation="eva", observation="obs")
    main.theme.set_theme("classic")
    main.theme.set_appearance("Light")
    monkeypatch.setattr(main, "load_settings", lambda: {"ui_theme": "classic", "appearance": "Light", "ui_scale": 1.0})
    app = main.App()
    app.update()
    return app, pid


def _silent():
    mb.showinfo = lambda *a, **k: None
    mb.showerror = lambda *a, **k: None
    mb.askyesno = lambda *a, **k: True
    fd.asksaveasfilename = lambda **kw: os.path.join(tempfile.mkdtemp(), "out")
    fd.askopenfilename = lambda **kw: ""


def test_more_main_paths(monkeypatch, tmp_path):
    _silent()
    app, pid = _fresh_app(monkeypatch, tmp_path)
    # context menu
    app._card_context(None, pid)  # no-op (event None)
    # edit selected
    app.selected_patient_id = pid
    app._edit_selected_patient() if hasattr(app, "_edit_selected_patient") else None
    # copy name
    app._copy_name_by_id(pid)
    # show shortcuts
    app._show_shortcuts()
    # toggle sidebar
    app._toggle_sidebar()
    app._toggle_sidebar()
    # responsive
    app._on_configure_responsive()
    # undo hint
    app._show_undo_hint()
    # view new
    app._show_view("new")
    app.update()
    # trash view + restore all (empty)
    app._show_view("trash")
    app.update()
    # settings view
    app._show_view("settings")
    app.update()
    # saveas view
    app._show_view("saveas")
    app.update()
    # backup view
    app._show_view("backup")
    app.update()
    app._show_view("patients")
    app.update()
    # delete + undo
    app._delete_by_id(pid)
    app.update()
    app._undo_last_delete()
    app.update()
    app.destroy()


def test_patient_panel_more(monkeypatch, tmp_path):
    _silent()
    app, pid = _fresh_app(monkeypatch, tmp_path)
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]
    # cancel new not applicable; test _edit_patient_info via dialog (patch)
    import patient_panel as pp
    class _StubDlg:
        def __init__(self, *a, **k):
            self.result = {"name": "Ana", "localitate": "Cluj", "sex": "F", "dob": "01.02.1990",
                           "diagnostic": "d", "objective": "o", "evaluation": "e", "observation": "ob"}
    monkeypatch.setattr(pp, "EditPatientDialog", _StubDlg)
    monkeypatch.setattr(panel, "wait_window", lambda w: None)
    panel._edit_patient_info()
    app.update()
    # keyboard shortcuts handler (no-op)
    panel._auto_save()
    app.destroy()


def test_new_patient_cancel(monkeypatch, tmp_path):
    _silent()
    app, pid = _fresh_app(monkeypatch, tmp_path)
    app._open_patient_by_id(None)
    app.update()
    panel = app.patient_panels.get(None)
    assert panel is not None
    panel._cancel_new()
    app.update()
    app.destroy()