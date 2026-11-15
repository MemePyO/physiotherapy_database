import main


def test_live_theme_switch(patient_app):
    app, pid = patient_app
    assert main.theme.active() == "classic"
    app._apply_ui_theme("medidash")
    app.update()
    assert main.theme.active() == "medidash"
    assert main.theme.layout() == "stacked"
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
