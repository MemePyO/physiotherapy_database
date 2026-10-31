# Changelog

## 1.0.0 (2026-10-31)

### Added
- Patient database desktop app (SQLite-backed) with CRUD, search, sort, soft-delete/trash with restore/purge, undo last delete (Ctrl+Z).
- Bilingual EN/RO, dark/light theme, UI scaling 100/125/150%.
- Attachments (any file type), patient history with full old/new text, clear history.
- Single-patient print/PDF, Save-as (Excel/CSV/PDF/Word), Excel export with field selection/order.
- Patient file embedded in right pane; avatar = initials circle; header with name/Code/DOB/Sex/Locality/Diagnostic/Last modified.
- Tabbed sections (Diagnostic/Obiectiv/Evaluare/Observație) with B/I/•/1. toolbar and hover tooltips.
- Auto-backup (last 7) in `backup\`, pre-migration backup.
- Responsive sidebar, slide-free instant card selection, debounced search, sort menu, counts, empty states.
- MediDashboard Pro theme (top bar, icon rail, stacked coloured sections, Bahnschrift font) selectable live in Settings.
- Inline new-patient preview with editable header.
- Inline attachment preview for images and PDFs.
- Bold/italic rendering in text editors.

### Fixed
- UI jump when returning to Patients view (grid weight reset).
- Sticky tooltip windows.
- Broken EditPatientDialog reference after module split.
- Broken Delete-patient menu item (referenced non-existent tree).
- Scroll crash on card selection.
- Data loss on patient switch (auto-save).

### Security / sanitization
- SQL audit (parameterized queries, whitelisted sort columns).
- Attachment filename sanitization and size cap (50 MB).
- Input length limits.
- PII redaction in logs.
- DB integrity check + WAL mode on startup.
- Pre-operation backups before import/purge.
- Removed legacy unused code.
