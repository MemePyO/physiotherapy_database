# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Diagnostics view (View > Diagnostics) with recent errors, health checks, startup self-test.
- Crash dumps (`crash_*.log`) with traceback, version, theme, and language.
- In-memory error ring buffer (last 50) in `log.py`.
- Global crash handler (`sys.excepthook`, `threading.excepthook`, `report_callback_exception`).
- Schema version tracking via `PRAGMA user_version` and `db.get_schema_version()`.
- Periodic integrity check (throttled, on view switch).
- Edit buttons for sessions, exercises, and VAS outcomes.
- "Tests" tab (renamed from "Rezultate (VAS)") containing VAS outcomes.
- Grouped Diagnostic/Objective/Evaluation/Observation into a browser-like tab view.
- All editable fields now shown in physio tables (modalities, notes, assigned date).
- New appointment form moved under the calendar in the left panel.
- Physio tabs embedded as a card in the scroll column (removed white stripe).
- Backup now uses SQLite backup API + WAL checkpoint for consistency.
- Backup pruning only removes app-generated `patients_*.db` (never `pre_*` safety copies).
- Startup self-test (DB integrity, schema version, settings, assets, backup folder, disk).

### Fixed
- `utils._exists` missing function definition (caused AttributeError in delayed callbacks).
- `patient_panel._now` NameError when adding VAS.
- Exercise NOT NULL constraint failure when patient unsaved.
- "Database is locked" on session add (removed per-connection WAL pragma; added busy_timeout).
- `search_entry` None crash on view switch.
- CTkFrame `takefocus` config error.
- Restore picking wrong backup by filename (now by mtime + init_db after restore).
- Backup pruning deleting safety copies.
- Benign Tk focus/destroy TclErrors on theme switch (suppressed + guarded).

### Changed
- Theme switch rebuilds UI with focus moved to main window first.
- `_backup_now` / `_auto_backup` use `db.backup_to()` instead of `shutil.copy2`.

## [1.0.0] - 2026-10-31

### Added
- Patient database desktop app (SQLite-backed) with CRUD, search, sort, soft-delete/trash with restore/purge, undo last delete (Ctrl+Z).
- Bilingual EN/RO, dark/light theme, UI scaling 100/125/150%.
- Attachments, patient history with full old/new text.
- Single-patient print/PDF, Save-as (Excel/CSV/PDF/Word), Excel export with field selection.
- Patient file embedded in right pane; avatar = initials circle.
- Tabbed sections (Diagnostic/Obiectiv/Evaluare/Observație) with B/I/•/1. toolbar.
- Auto-backup (last 7) in `backup\`, pre-migration backup.
- Responsive sidebar, debounced search, sort menu, counts, empty states.
- MediDashboard Pro theme selectable live in Settings.
- Inline new-patient preview with editable header.
- Inline attachment preview for images and PDFs.

### Fixed
- UI jump when returning to Patients view.
- Sticky tooltip windows.
- Broken EditPatientDialog reference after module split.
- Broken Delete-patient menu item.
- Scroll crash on card selection.
- Data loss on patient switch (auto-save).

### Security
- Parameterized SQL, whitelisted sort columns.
- Attachment filename sanitization and 50 MB size cap.
- Input length limits.
- PII redaction in logs.
- DB integrity check + WAL mode on startup.
- Pre-operation backups before import/purge.