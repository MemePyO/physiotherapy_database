import main


def test_live_theme_switch(patient_app):
    app, pid = patient_app
    assert main.theme.active() == "classic"
    app._apply_ui_theme("medidash")
    app.update()
    assert main.theme.active() == "medidash"
    assert main.theme.layout() == "stacked"
    # medidash has the same inline search row as classic
    assert app.search_entry is not None
    assert app.search_entry.winfo_exists()
    app.search_entry.insert(0, "zzz-no-match")
    app.refresh_patients_db()
    app._clear_search()
    assert app.search_entry.get() == ""
    # patient file opens in stacked mode
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]
    assert panel.tabview is not None
    assert hasattr(panel, "sections_frame")
    assert hasattr(panel, "plan_entries")
    app._apply_ui_theme("classic")
    app.update()
    assert main.theme.active() == "classic"


def test_settings_dialog_highlights_active_options(patient_app):
    from dialogs import SettingsDialog

    app, _pid = patient_app
    dialog = SettingsDialog(app)
    try:
        assert dialog.scale_buttons[100][1] is True
        assert dialog.scale_buttons[125][1] is False
        assert dialog.theme_buttons["classic"][1] is True
        assert dialog.theme_buttons["medidash"][1] is False
        active_btn = dialog.theme_buttons["classic"][0]
        inactive_btn = dialog.theme_buttons["medidash"][0]
        assert active_btn.cget("fg_color") == main.theme.ACCENT
        assert inactive_btn.cget("fg_color") == main.theme.MUTED_BTN
    finally:
        dialog.destroy()
