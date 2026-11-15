import db
import main


def test_all_views_render(patient_app):
    app, _pid = patient_app
    for v in ("patients", "trash", "settings", "saveas", "backup", "new"):
        app._show_view(v)
        app.update()
    app._show_view("patients")
    app.update()


def test_patient_panel_actions(patient_app):
    app, pid = patient_app
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


def test_medidash_views(fresh_db, silent_dialogs):
    db.add_patient("Bob", "Iasi")
    main.theme.set_theme("medidash")
    medidash_app = main.App()
    medidash_app.update()
    medidash_app._show_view("patients")
    medidash_app.update()
    pid = db.get_all_patients()[0]["id"]
    medidash_app._open_patient_by_id(pid)
    medidash_app.update()
    panel = medidash_app.patient_panels[pid]
    panel.diagnostic_text.insert("1.0", "x")
    panel.mark_dirty()
    panel._save_all(silent=True)
    medidash_app.update()
    medidash_app._apply_ui_theme("classic")
    medidash_app.update()
    medidash_app.destroy()
    main.theme.set_theme("classic")
