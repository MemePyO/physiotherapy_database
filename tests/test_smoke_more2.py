import main


def test_more_main_paths2(patient_app, monkeypatch):
    app, pid = patient_app
    monkeypatch.setattr(main.App, "wait_window", lambda self, w: None)
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


def test_more_panel_paths(patient_app):
    app, pid = patient_app
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
