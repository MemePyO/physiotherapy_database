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


def test_settings_dialog_stays_open_when_theme_changes(patient_app):
    from dialogs import SettingsDialog

    app, _pid = patient_app
    dialog = SettingsDialog(app)
    try:
        dialog._choose_theme("medidash")
        app.update()
        assert dialog.winfo_exists()
        assert main.theme.active() == "medidash"
        assert dialog.theme_buttons["medidash"][1] is True
        assert dialog.theme_buttons["classic"][1] is False
        assert dialog.theme_buttons["medidash"][0].cget("fg_color") == main.theme.ACCENT
        assert dialog.theme_buttons["classic"][0].cget("fg_color") == main.theme.MUTED_BTN
    finally:
        dialog.destroy()


def test_settings_dialog_appearance_highlight_refreshes(patient_app):
    from dialogs import SettingsDialog

    app, _pid = patient_app
    dialog = SettingsDialog(app)
    try:
        dialog._choose_appearance("Dark")
        app.update()
        assert main.theme.active() == "classic-dark"
        assert dialog.appearance_buttons["Dark"][1] is True
        assert dialog.appearance_buttons["Light"][1] is False
        assert dialog.appearance_buttons["Dark"][0].cget("fg_color") == main.theme.ACCENT
    finally:
        dialog.destroy()
        app._apply_appearance("Light")


def test_view_switch_keeps_search_and_list(patient_app):
    app, _pid = patient_app
    app._show_view("settings")
    app.update()
    assert app._current_view == "settings"
    app._show_view("patients")
    app.update()
    assert app._current_view == "patients"
    assert app.search_entry.winfo_exists()
    assert app.card_list.winfo_exists()
