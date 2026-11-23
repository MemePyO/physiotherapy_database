"""Language switching, panel key handling and settings-dialog refresh tests."""

import main


def test_language_switch_rebuilds_and_keeps_state(patient_app):
    app, pid = patient_app
    try:
        app._show_view("patients")
        app.update()
        app.search_entry.insert(0, "Ana")
        app._search_text = "Ana"
        app._open_patient_by_id(pid)
        app.update()

        app._on_language_change("Română")
        app.update()

        assert main.lang.get_language() == "ro"
        assert app._lang_var.get() == "ro"
        assert app.winfo_exists()
        assert app._current_view == "patients"
        assert app.search_entry.winfo_exists()
        assert app.search_entry.get() == "Ana"
        assert app.selected_patient_id == pid
        assert app.title() == main.lang.t("app_name")
    finally:
        try:
            main.lang.set_language("en")
        except Exception:
            pass


def test_language_round_trip(patient_app):
    app, _pid = patient_app
    try:
        app._on_language_change("Română")
        app.update()
        assert main.lang.get_language() == "ro"
        app._on_language_change("English")
        app.update()
        assert main.lang.get_language() == "en"
        assert app._current_view == "patients"
    finally:
        try:
            main.lang.set_language("en")
        except Exception:
            pass


def test_settings_dialog_refreshes_after_language_change(patient_app):
    from dialogs import SettingsDialog

    app, _pid = patient_app
    dialog = SettingsDialog(app)
    try:
        app.update()
        assert dialog.lang_menu.get() == "English"

        dialog._choose_language("Română")
        app.update()
        app.update()

        assert dialog.winfo_exists()
        assert dialog.lang_menu.get() == "Română"
        assert dialog.title() == main.lang.t("ui_settings")
    finally:
        try:
            dialog.destroy()
        except Exception:
            pass
        try:
            main.lang.set_language("en")
            main.save_language("en")
        except Exception:
            pass


def test_panel_key_handler_tolerates_missing_event(patient_app):
    app, pid = patient_app
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]
    panel._dirty = False
    panel._on_key_release(None, "diagnostic", panel.diagnostic_text)
    assert panel._dirty is True
