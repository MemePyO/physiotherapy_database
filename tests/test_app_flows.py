"""Application-level flow tests: calendar, diagnostics, backup/restore, import."""

import os

import db
import main
from services.appointment_service import get_appointment_service
from services.patient_service import get_patient_service


class _SyncTask:
    """Deterministic stand-in for ``workers.BackgroundTask``."""

    def __init__(self, owner, work, on_done=None, on_error=None, on_progress=None):
        self.work = work
        self.on_done = on_done
        self.on_error = on_error
        self.on_progress = on_progress

    def start(self):
        try:
            result = self.work(self.on_progress or (lambda message: None))
        except Exception as exc:  # noqa: BLE001 - mirrors worker behaviour
            if self.on_error:
                self.on_error(exc)
        else:
            if self.on_done:
                self.on_done(result)


def test_calendar_and_diagnostics_flows(patient_app):
    app, pid = patient_app
    app._show_view("calendar")
    app.update()

    app._cal_time_var.set("10:30")
    app._cal_dur_var.set("45")
    app._cal_notes_entry.delete(0, "end")
    app._cal_notes_entry.insert(0, "first visit")
    app._cal_add_appointment()
    app.update()

    appointments = get_appointment_service().list()
    assert len(appointments) == 1
    assert appointments[0]["patient_id"] == pid
    assert appointments[0]["duration_min"] == 45
    assert appointments[0]["notes"] == "first visit"
    assert "10:30" in appointments[0]["datetime"]

    # invalid time is rejected without creating another appointment
    app._cal_time_var.set("25:99")
    app._cal_add_appointment()
    assert app._cal_err.cget("text")
    assert len(get_appointment_service().list()) == 1

    # day view lists the existing appointment and status edits persist
    day = app._cal_selected_day
    app._show_day_appointments(day)
    app.update()
    aid = appointments[0]["id"]
    get_appointment_service().update(aid, status="done")
    assert get_appointment_service().list()[0]["status"] == "done"

    app._show_view("diagnostics")
    app.update()
    assert app._current_view == "diagnostics"
    app._show_view("settings")
    app.update()
    assert app._current_view == "settings"


def test_backup_restore_and_attachment_copy(patient_app, monkeypatch, tmp_path):
    app, pid = patient_app
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(main, "_data_dir", lambda: str(data_dir))
    monkeypatch.setattr(main, "BackgroundTask", _SyncTask)

    attachments = data_dir / "attachments"
    attachments.mkdir()
    (attachments / "note.txt").write_text("hello", encoding="utf-8")
    backup_dir = data_dir / "backup"
    backup_dir.mkdir()
    for index in range(8):
        old = backup_dir / ("patients_old%d.db" % index)
        old.write_text("", encoding="utf-8")
        os.utime(old, (index, index))

    app._backup_now()

    names = os.listdir(backup_dir)
    assert any(name.startswith("attachments_") for name in names)
    backup_files = [name for name in names if name.startswith("patients_") and name.endswith(".db")]
    # pruning keeps the seven newest automatic backups
    assert len(backup_files) == 7

    snapshot = sorted(backup_files)[-1]

    class _Dialog:
        def __init__(self, master, folder, files):
            self.result = snapshot

    monkeypatch.setattr(db, "_data_dir", lambda: str(tmp_path / "dbdata"))
    monkeypatch.setattr(main, "RestoreBackupDialog", _Dialog)
    monkeypatch.setattr(main.App, "wait_window", lambda self, window: None)
    app._restore_backup()
    app.update()
    assert any(p["id"] == pid for p in get_patient_service().list_patients())

    # no backup folder is a no-op
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(main, "_data_dir", lambda: str(empty))
    app._restore_backup()
    app.update()

    # corrupt snapshots are rejected before replacing the live database
    corrupt = tmp_path / "corrupt"
    (corrupt / "backup").mkdir(parents=True)
    (corrupt / "backup" / "patients_bad.db").write_text("not a database", encoding="utf-8")

    class _BadDialog:
        def __init__(self, master, folder, files):
            self.result = "patients_bad.db"

    errors = []
    monkeypatch.setattr(main, "_data_dir", lambda: str(corrupt))
    monkeypatch.setattr(main, "RestoreBackupDialog", _BadDialog)
    monkeypatch.setattr(main, "report_error", lambda message: errors.append(message))
    app._restore_backup()
    assert errors


def test_import_data_from_csv_and_cancel(patient_app, monkeypatch, tmp_path):
    app, _pid = patient_app
    monkeypatch.setattr(main, "_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(db, "_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(main, "BackgroundTask", _SyncTask)

    before = {p["name"] for p in get_patient_service().list_patients()}
    monkeypatch.setattr(main.filedialog, "askopenfilename", lambda **kwargs: "")
    app._import_data()
    assert {p["name"] for p in get_patient_service().list_patients()} == before

    csv_file = tmp_path / "import.csv"
    csv_file.write_text(
        "nume;localitate;diagnostic;obiectiv;evaluare;observatie\n"
        "Ion Import;Cluj;Lombalgie;mobilitate;evaluare;observatie\n"
        ";;; ;;\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main.filedialog, "askopenfilename", lambda **kwargs: str(csv_file))
    app._import_data()
    app.update()

    names = {p["name"] for p in get_patient_service().list_patients()}
    assert "Ion Import" in names


def test_prune_auto_backups_keeps_safety_copies(tmp_path):
    from main import _prune_auto_backups

    for index in range(9):
        path = tmp_path / ("patients_%d.db" % index)
        path.write_text("", encoding="utf-8")
        os.utime(path, (index, index))
    (tmp_path / "pre_migration_1.db").write_text("", encoding="utf-8")

    _prune_auto_backups(str(tmp_path), keep=3)

    names = set(os.listdir(tmp_path))
    assert len([n for n in names if n.startswith("patients_")]) == 3
    assert "pre_migration_1.db" in names
