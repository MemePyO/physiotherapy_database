"""Regression tests for the decomposed patient-file panel sections."""

import os

from services.physio_service import get_physio_service


def _panel(patient_app):
    app, pid = patient_app
    app._open_patient_by_id(pid)
    app.update()
    return app.patient_panels[pid], pid


def test_panel_section_controllers_and_shared_patient(patient_app):
    from ui.patient_panel.attachments_section import AttachmentsSection
    from ui.patient_panel.exercises_section import ExercisesSection
    from ui.patient_panel.outcomes_section import OutcomesSection
    from ui.patient_panel.plan_section import PlanSection
    from ui.patient_panel.sessions_section import SessionsSection

    panel, pid = _panel(patient_app)
    expected = (
        (panel.plan_section, PlanSection),
        (panel.sessions_section, SessionsSection),
        (panel.exercises_section, ExercisesSection),
        (panel.outcomes_section, OutcomesSection),
        (panel.attachments_section, AttachmentsSection),
    )
    for section, kind in expected:
        assert isinstance(section, kind)
        assert section.patient_id == pid
    # historical widget attributes survive the extraction for compatibility
    for attr in ("plan_entries", "ses_tree", "hep_tree", "out_tree", "attach_tree"):
        assert hasattr(panel, attr)


def test_plan_section_roundtrip_and_invalid_count(patient_app):
    panel, pid = _panel(patient_app)
    panel.plan_entries["diagnosis_code"].delete(0, "end")
    panel.plan_entries["diagnosis_code"].insert(0, "M54.5")
    panel.plan_entries["prescribed_sessions"].delete(0, "end")
    panel.plan_entries["prescribed_sessions"].insert(0, "12")
    panel.plan_goals.delete("1.0", "end")
    panel.plan_goals.insert("1.0", "reduce pain")

    panel._save_plan()

    saved = get_physio_service().get_plan(pid)
    assert saved["diagnosis_code"] == "M54.5"
    assert saved["prescribed_sessions"] == 12
    assert saved["goals"] == "reduce pain"

    # clear widgets then let the section load them back
    panel.plan_entries["diagnosis_code"].delete(0, "end")
    panel.plan_section.load()
    assert panel.plan_entries["diagnosis_code"].get() == "M54.5"

    # invalid session counts fall back to zero instead of failing the save
    panel.plan_entries["prescribed_sessions"].delete(0, "end")
    panel.plan_entries["prescribed_sessions"].insert(0, "not-a-number")
    panel._save_plan()
    assert get_physio_service().get_plan(pid)["prescribed_sessions"] == 0


def test_sessions_section_flow_and_unsaved_warning(patient_app, monkeypatch):
    from dialogs import input_dialog

    panel, pid = _panel(patient_app)
    monkeypatch.setattr(input_dialog, "ask_string", lambda *a, **k: "01.02.2026")
    panel._add_session()

    sessions = get_physio_service().list_sessions(pid)
    assert len(sessions) == 1
    sid = sessions[0]["id"]

    monkeypatch.setattr(
        panel,
        "_show_editor",
        lambda title, fields, values: {
            "session_no": "3",
            "date": "02.02.2026",
            "duration_min": "45",
            "pain_before": "6",
            "pain_after": "2",
            "status": "done",
            "modalities": "TENS",
            "exercises": "bridge",
            "notes": "ok",
        },
    )
    panel.ses_tree.selection_set(str(sid))
    panel._edit_session()
    updated = [s for s in get_physio_service().list_sessions(pid) if s["id"] == sid][0]
    assert updated["session_no"] == 3
    assert updated["duration_min"] == 45
    assert updated["pain_after"] == 2

    panel.ses_tree.selection_set(str(sid))
    panel._delete_session()
    assert get_physio_service().list_sessions(pid) == []

    # an unsaved panel cannot create domain records
    app = patient_app[0]
    app._open_patient_by_id(None)
    app.update()
    new_panel = app.patient_panels[None]
    called = []
    monkeypatch.setattr(new_panel.sessions_section, "info", lambda msg: called.append(msg))
    new_panel._add_session()
    assert called


def test_exercises_section_flow_and_defaults(patient_app, monkeypatch):
    from dialogs import input_dialog

    panel, pid = _panel(patient_app)
    monkeypatch.setattr(input_dialog, "ask_string", lambda *a, **k: "Bridge")
    panel._add_exercise()

    exercises = get_physio_service().list_exercises(pid)
    assert [e["name"] for e in exercises] == ["Bridge"]
    eid = exercises[0]["id"]

    monkeypatch.setattr(
        panel,
        "_show_editor",
        lambda title, fields, values: {
            "name": "Bridge advanced",
            "sets": "4",
            "reps": "12",
            "hold_sec": "5",
            "frequency": "daily",
            "assigned_date": "01.02.2026",
            "notes": "progress",
        },
    )
    panel.hep_tree.selection_set(str(eid))
    panel._edit_exercise()
    updated = [e for e in get_physio_service().list_exercises(pid) if e["id"] == eid][0]
    assert updated["name"] == "Bridge advanced"
    assert updated["sets"] == 4
    assert updated["hold_sec"] == 5

    # blank numeric fields use the documented defaults
    monkeypatch.setattr(
        panel,
        "_show_editor",
        lambda title, fields, values: {
            "name": "Plank",
            "sets": "",
            "reps": "",
            "hold_sec": "",
            "frequency": "",
            "assigned_date": "",
            "notes": "",
        },
    )
    panel.hep_tree.selection_set(str(eid))
    panel._edit_exercise()
    defaults = [e for e in get_physio_service().list_exercises(pid) if e["id"] == eid][0]
    assert (defaults["sets"], defaults["reps"], defaults["hold_sec"]) == (3, 10, 0)

    panel.hep_tree.selection_set(str(eid))
    panel._delete_exercise()
    assert get_physio_service().list_exercises(pid) == []


def test_outcomes_section_validation_and_flow(patient_app, monkeypatch):
    from dialogs import input_dialog

    panel, pid = _panel(patient_app)
    errors = []
    monkeypatch.setattr(
        "ui.patient_panel.outcomes_section.report_error", lambda msg: errors.append(msg)
    )

    monkeypatch.setattr(input_dialog, "ask_string", lambda *a, **k: "nope")
    panel._add_outcome()
    assert errors == ["Valoare invalidă."]

    monkeypatch.setattr(input_dialog, "ask_string", lambda *a, **k: "11")
    panel._add_outcome()
    assert errors[-1] == "VAS trebuie 0-10."
    assert get_physio_service().list_outcomes(pid) == []

    monkeypatch.setattr(input_dialog, "ask_string", lambda *a, **k: "7")
    panel._add_outcome()
    outcomes = get_physio_service().list_outcomes(pid)
    assert len(outcomes) == 1
    oid = outcomes[0]["id"]

    monkeypatch.setattr(
        panel,
        "_show_editor",
        lambda title, fields, values: {
            "measure": "NRS",
            "value": "4",
            "date": "03.02.2026",
            "notes": "follow-up",
        },
    )
    panel.out_tree.selection_set(str(oid))
    panel._edit_outcome()
    updated = [o for o in get_physio_service().list_outcomes(pid) if o["id"] == oid][0]
    assert updated["measure"] == "NRS"
    assert updated["value"] == 4

    panel.out_tree.selection_set(str(oid))
    panel._delete_outcome()
    assert get_physio_service().list_outcomes(pid) == []


def test_attachments_section_flow(patient_app, monkeypatch, tmp_path):
    from services.attachment_service import get_attachment_service
    from ui.patient_panel import attachments_section

    panel, pid = _panel(patient_app)
    sample = tmp_path / "note.txt"
    sample.write_text("hello", encoding="utf-8")
    monkeypatch.setattr(attachments_section.filedialog, "askopenfilename", lambda **kw: str(sample))
    panel._attach_file()
    children = panel.attach_tree.get_children()
    assert len(children) == 1

    panel.attach_tree.selection_set(children[0])
    panel._delete_attachment()
    assert panel.attach_tree.get_children() == ()

    # non-image attachments fall back to the OS viewer
    sample = tmp_path / "raw.dat"
    sample.write_text("data", encoding="utf-8")
    get_attachment_service().add(pid, str(sample))
    panel._load_attachments()
    child = panel.attach_tree.get_children()[0]
    panel.attach_tree.selection_set(child)
    opened = []
    monkeypatch.setattr(panel.attachments_section, "open_attachment", lambda: opened.append(True))
    panel._preview_attachment()
    assert opened == [True]

    # a missing stored file is reported instead of crashing
    del panel.attachments_section.open_attachment
    record = get_attachment_service().list(pid)[0]
    os.remove(record["stored_path"])
    panel._load_attachments()
    panel.attach_tree.selection_set(panel.attach_tree.get_children()[0])
    errors = []
    monkeypatch.setattr(attachments_section, "report_error", lambda msg: errors.append(str(msg)))
    panel._open_attachment()
    assert errors
