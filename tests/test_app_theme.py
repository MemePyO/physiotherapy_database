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
