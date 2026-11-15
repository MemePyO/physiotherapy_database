import ui.patient_panel as pp


def test_more_main_paths(patient_app):
    app, pid = patient_app
    # context menu
    app._card_context(None, pid)  # no-op (event None)
    # edit selected
    app.selected_patient_id = pid
    app._edit_selected_patient() if hasattr(app, "_edit_selected_patient") else None
    # copy name
    app._copy_name_by_id(pid)
    # show shortcuts
    app._show_shortcuts()
    # toggle sidebar
    app._toggle_sidebar()
    app._toggle_sidebar()
    # responsive
    app._on_configure_responsive()
    # undo hint
    app._show_undo_hint()
    # view new
    app._show_view("new")
    app.update()
    # trash view + restore all (empty)
    app._show_view("trash")
    app.update()
    # settings view
    app._show_view("settings")
    app.update()
    # saveas view
    app._show_view("saveas")
    app.update()
    # backup view
    app._show_view("backup")
    app.update()
    app._show_view("patients")
    app.update()
    # delete + undo
    app._delete_by_id(pid)
    app.update()
    app._undo_last_delete()
    app.update()


def test_patient_panel_more(patient_app, monkeypatch):
    app, pid = patient_app
    app._open_patient_by_id(pid)
    app.update()
    panel = app.patient_panels[pid]

    class _StubDlg:
        def __init__(self, *a, **k):
            self.result = {
                "name": "Ana",
                "localitate": "Cluj",
                "sex": "F",
                "dob": "01.02.1990",
                "diagnostic": "d",
                "objective": "o",
                "evaluation": "e",
                "observation": "ob",
            }

    monkeypatch.setattr(pp, "EditPatientDialog", _StubDlg)
    monkeypatch.setattr(panel, "wait_window", lambda w: None)
    panel._edit_patient_info()
    app.update()
    # keyboard shortcuts handler (no-op)
    panel._auto_save()


def test_new_patient_cancel(patient_app):
    app, _pid = patient_app
    app._open_patient_by_id(None)
    app.update()
    panel = app.patient_panels.get(None)
    assert panel is not None
    panel._cancel_new()
    app.update()
