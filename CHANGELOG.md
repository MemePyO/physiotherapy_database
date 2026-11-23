# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - 2026-11-23

### Added
- Live language switching: window, menus, views and an open Settings dialog re-render immediately (no restart).
- Menu accelerators for save-as, backup, restore, import, open file, theme, diagnostics, quit and help.
- Zoom shortcuts `Ctrl+=` / `Ctrl+-` / `Ctrl+0` over 100/125/150 %, plus a View > Zoom submenu.
- Language menu entries show a check mark on the active language.
- About dialog now shows build time, schema version, theme, language and the data folder.
- Windows executable version resource (`version_info.txt`) for product/file metadata.
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
- Performance indexes for patient search/sort, sessions, appointments, outcomes, exercises and history (migration v2).
- Service layer for physiotherapy data, appointments, attachments, history, backups and database lifecycle; UI now depends only on services.
- Shared pytest fixtures (`tests/conftest.py`) and architecture/allowlist/backup tests.
- CI gates: 60% coverage (`pytest-cov`), `mypy` on `db.py` + `services/`, architecture test preventing UI → `db` imports.
- `error_ui.report_error()` as the single, non-raising error-dialog entry point.

### Removed
- Unused `app/` package (empty aspirational structure, zero imports).
- Unused `localization/` package and JSON catalogs (the app uses `lang.py`).
- Duplicate `services/migration_manager.py` (superseded by `data.migrations`).
- Duplicate `services/background_tasks.py` re-export shim (use `workers.BackgroundTask`).
- Runtime data accidentally tracked in git (`.coverage`, `patients.db`, `backup/*.db`).

### Fixed
- Crash dumps (`crash_*.log`) are written to the writable data folder instead of beside the executable.
- Patient panel key handler no longer raises when Tk invokes it without an event.
- Test suite no longer writes to the real per-user data folder (settings, logs, backups, crash dumps).
- Pre-operation and pre-migration backups silently failed (`datetime.datetime.now()` on a `from datetime import datetime` import).
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
- Theme switch recolours the window in place; layout switches and view changes are covered by a veil so no blank frame is visible.
- `classic` now has a real dark palette (`classic-dark`) instead of mixing light colours with a dark title bar.
- UI scale is tracked explicitly; `ttk` tables scale row height and heading font with the rest of the interface.
- Dialogs grow to fit their content instead of clipping it at 125 % / 150 %.
- Restored window geometry is clamped to the visible screen so the window cannot open off-screen.
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