def test_add_patient_dialog_opens(app):
    from dialogs import AddPatientDialog

    dlg = AddPatientDialog(app)
    app.update()
    dlg.destroy()


def test_settings_dialog_opens(app):
    from dialogs import SettingsDialog

    dlg = SettingsDialog(app)
    app.update()
    dlg.destroy()


def test_export_fields_dialog_opens(app):
    from dialogs import ExportFieldsDialog
    from main import EXPORT_FIELDS

    dlg = ExportFieldsDialog(app, EXPORT_FIELDS, initial=[k for k, _ in EXPORT_FIELDS])
    app.update()
    dlg.destroy()


def test_trash_dialog_opens(app):
    from dialogs import TrashDialog

    dlg = TrashDialog(app)
    app.update()
    dlg.destroy()


def test_restore_backup_dialog_opens(app, tmp_path):
    from dialogs import RestoreBackupDialog

    dlg = RestoreBackupDialog(app, str(tmp_path), [])
    app.update()
    dlg.destroy()
