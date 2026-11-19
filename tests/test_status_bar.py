"""Footer status strip: patient, save state, timestamp and patient count."""

import lang


def test_status_bar_tracks_patient_state(patient_app):
    app, pid = patient_app
    assert app._status_bar.winfo_exists()
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]

    assert "Ana Test" in app._status_patient_lbl.cget("text")
    assert app._status_count_lbl.cget("text") == lang.t("ui_patients_count", n=1)

    panel.mark_dirty()
    assert app._status_state_lbl.cget("text") == lang.t("ui_unsaved")

    panel._save_all(silent=True)
    assert lang.t("ui_saved") in app._status_state_lbl.cget("text")


def test_status_callback_is_optional_and_guarded(app):
    from ui.patient_panel import PatientFilePanel

    def boom(_patient_id, _state):
        raise RuntimeError("status callback failure")

    panel = PatientFilePanel(app.file_host, None, new=True, on_status=boom)
    panel.mark_dirty()  # swallowed by the panel
    panel._auto_save()  # new panels are skipped
    panel._cancel_new()

    silent = PatientFilePanel(app.file_host, None, new=True)
    silent.mark_dirty()
    silent._cancel_new()
