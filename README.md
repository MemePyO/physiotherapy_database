# Patient Database (Physiotherapy)

A Windows desktop application for managing physiotherapy patient records, treatment plans, sessions, VAS outcome measures, home exercise programs (HEP), and an appointment calendar. Built with CustomTkinter and SQLite.

## Features

- **Patient records** — name, locality, sex, DOB, diagnostic, objective, evaluation, observation (bilingual EN/RO).
- **Treatment plans** — ICD code, body region, side, prescribed sessions, dates, goals, contraindications, notes.
- **Sessions** — date, duration, modalities, exercises, pain before/after (VAS), status.
- **Home Exercise Program (HEP)** — name, sets, reps, hold time, frequency, assigned date, notes.
- **Outcome measures** — VAS/NRS tracking over time.
- **Appointment calendar** — month grid with inline schedule preview and new-appointment form.
- **Export** — Excel, CSV, PDF, Word with selectable fields.
- **Backup/Restore** — automatic daily backups (last 7), manual backup, restore with verification.
- **Diagnostics view** — recent errors, health checks, startup self-test.
- **Themes** — Classic and MediDashboard (light/dark), UI scaling 100/125/150%.
- **Bilingual** — English and Romanian.

## Requirements

- Python 3.10+ (tested on 3.14)
- Dependencies:
  ```
  pip install -r requirements.txt
  ```

## Installation

```bash
git clone <repo-url>
cd physiotherapy_database
pip install -r requirements.txt
python main.py
```

## Configuration

Settings are stored in `settings.json` (auto-created):
- `ui_theme`: "classic" or "medidash"
- `appearance`: "Light" or "Dark"
- `ui_scale`: 1.0, 1.25, or 1.5
- `ui_language`: "en" or "ro"
- `sort_by`, `sort_dir`: patient list sorting

## Project Structure

```
physiotherapy_database/
├── main.py              # Application entry point, views, navigation
├── ui/                  # UI components
│   └── patient_panel/   # Embedded patient file panel (package)
├── services/            # Business logic (patient, export, validation, migration)
├── data/                # Data access and migrations
├── localization/        # Language files (en.json, ro.json)
├── dialogs/             # Dialog windows (package)
├── db.py                # SQLite schema, CRUD, migrations, backup
├── lang.py              # Bilingual string table (EN/RO) [legacy]
├── theme.py             # Theme tokens (classic/medidash, light/dark)
├── utils.py             # Helpers (normalization, validation, PDF, etc.)
├── tooltip.py           # Hover tooltips
├── log.py               # Centralized logging (rotating file + ring buffer)
├── paths.py             # Data directory and single-instance lock
├── workers.py           # Background task runner
├── version.py           # App version
├── assets/              # Images, icons
├── backup/              # Database backups (auto + manual)
├── attachments/         # Patient file attachments
├── tests/               # pytest test suite (43 tests)
└── dist/                # Built executable (PyInstaller)
```

## Database Architecture

SQLite with WAL mode. Tables:
- `patients` — master patient records
- `deleted_patients` — soft-deleted patients (trash)
- `treatment_plans` — ICD code, body region, goals, etc.
- `sessions` — therapy sessions with VAS before/after
- `appointments` — scheduled appointments
- `outcome_measures` — VAS/NRS tracking
- `exercises` — home exercise program (HEP)
- `patient_history` — audit trail of text changes
- `attachments` — file attachments metadata

Schema version tracked via `PRAGMA user_version`. WAL checkpoint runs before every backup. Backups use SQLite's backup API for consistency.

## Build Instructions

```bash
# Install PyInstaller
pip install pyinstaller

# Build (Windows)
build.bat
```

Output: `dist\PhysioDatabase.exe` (single-file, windowed).

## Troubleshooting

- **"Database is locked"**: Close other instances. The app uses a 15s busy timeout.
- **Missing tables after restore**: The app runs `db.init_db()` after restore to ensure schema.
- **Blank/white areas in UI**: Switch themes in Settings.
- **Logs**: Check `app.log` in the app directory (or `dist\app.log` for the exe).
- **Diagnostics**: View > Diagnostics shows recent errors, health checks, and startup self-test results.

## License

Private / internal use.