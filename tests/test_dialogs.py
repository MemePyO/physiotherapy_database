import sys, os, tempfile, tkinter.filedialog as fd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


def _fresh_app(monkeypatch, tmp_path):
    d = tempfile.mkdtemp()
    dbfile = os.path.join(d, "test.db")
    monkeypatch.setattr(db, "db_path", lambda: dbfile)
    db.init_db()
    import main
    main.theme.set_theme("classic")
    main.theme.set_appearance("Light")
    monkeypatch.setattr(main, "load_settings", lambda: {"ui_theme": "classic", "appearance": "Light", "ui_scale": 1.0})
    app = main.App()
    app.update()
    return app


def test_add_patient_dialog_opens(monkeypatch, tmp_path):
    app = _fresh_app(monkeypatch, tmp_path)
    from dialogs import AddPatientDialog
    dlg = AddPatientDialog(app)
    app.update()
    dlg.destroy()
    app.destroy()


def test_settings_dialog_opens(monkeypatch, tmp_path):
    app = _fresh_app(monkeypatch, tmp_path)
    from dialogs import SettingsDialog
    dlg = SettingsDialog(app)
    app.update()
    dlg.destroy()
    app.destroy()


def test_export_fields_dialog_opens(monkeypatch, tmp_path):
    app = _fresh_app(monkeypatch, tmp_path)
    from dialogs import ExportFieldsDialog
    from main import EXPORT_FIELDS
    dlg = ExportFieldsDialog(app, EXPORT_FIELDS, initial=[k for k, _ in EXPORT_FIELDS])
    app.update()
    dlg.destroy()
    app.destroy()


def test_trash_dialog_opens(monkeypatch, tmp_path):
    app = _fresh_app(monkeypatch, tmp_path)
    from dialogs import TrashDialog
    dlg = TrashDialog(app)
    app.update()
    dlg.destroy()
    app.destroy()


def test_restore_backup_dialog_opens(monkeypatch, tmp_path):
    app = _fresh_app(monkeypatch, tmp_path)
    from dialogs import RestoreBackupDialog
    import os, tempfile
    folder = tempfile.mkdtemp()
    dlg = RestoreBackupDialog(app, folder, [])
    app.update()
    dlg.destroy()
    app.destroy()