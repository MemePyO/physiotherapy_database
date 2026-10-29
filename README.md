# Appointment Tracker (Desktop)

A Windows desktop app for tracking patient appointments and exporting them to
Excel, with the same `X` / `L` / `C` / empty pattern used in the monthly tables.

**Web version (phone):** https://memepyo.github.io/appointment-tracker/ —
[web app repo](https://github.com/MemePyO/appointment-tracker)

## Legend

| Cell | Meaning |
|------|---------|
| `X` | Appointment |
| `L` | Legal free day |
| `C` | Free day |
| *(empty)* | Not there |

`X` always wins over `L`/`C`.

## Features

- Modern GUI (CustomTkinter), 1120×760
- **Add / edit / remove patients** with appointment days (`1, 5, 12-14`)
- **Autocomplete** patient names — every name you enter is remembered in `patients.json`
- **Pattern for all patients** — same `C` / `L` free days applied to everyone
- **Counts** (`X`) per patient, shown live in the table
- **Save / load projects** (`.json`)
- **Year field** next to Month (defaults to the current year; saved/loaded with the project)
- **Export choice** — Export asks whether to **update an existing workbook**
  (pick the file; same-month collision still asks before replacing) or to
  **create a new one** (Windows overwrite prompt). The chosen file is remembered.
- **Introdu ședință tab** — mark one appointment by date (e.g. STOICA FLORIN,
  30.04.2026): puts an `X` on that patient's day in the matching `MM.YYYY` sheet,
  adds the patient (styled row, COUNTIF/TOTAL kept correct) if missing, creates the
  sheet if missing, and does nothing if the `X` is already there.
- **Auto L days** — the **auto** button next to L days fills the field with every
  Saturday and Sunday of the chosen Month + Year
- **Language selector** — switch the interface (labels, buttons, dialogs, errors)
  between English and Română; remembered between launches. Month names
  (`ianuarie…decembrie`) and exported Excel headers stay Romanian always
- **Multi-sheet Excel workbook** — one sheet per month, named from the Month + Year
  fields (`septembrie` + `2026` → sheet `09.2026`). Every export goes into the same
  `.xlsx`; if that month's sheet already exists a popup asks whether to replace it
  or keep the old one, all other months are kept. Month accepts `ianuarie…decembrie`
  (any case) or a number like `9`.
- **Export real `.xlsx`** — title row, per-day columns (1–31), `COUNTIF` formulas, `TOTAL` row with `SUM`, color-coded cells
- **Remembers the last export workbook** (in `settings.json`), so the next export
  preselects the same file
- **Phone ↔ PC** — load/export the same `.json` project format as the web app

## Requirements

- Python 3.10+ (tested on 3.14)
- Dependencies:

```
pip install customtkinter openpyxl
```

## Run

```
python appointment_tracker.py
```

## Files

| File | Role |
|------|------|
| `appointment_tracker.py` | Launcher |
| `frontend.py` | GUI (CustomTkinter) + autocomplete widget |
| `backend.py` | Core logic: parsing, validation, patient registry, Excel table layout |
| `workbook.py` | Multi-sheet Excel workbook export (one sheet per month, `MM.YYYY`) |
| `sheet_check.py` | Replace-existing-sheet confirmation popup |
| `appointment.py` | "Introdu ședință" tab: mark an X by date into the workbook |
| `weekend.py` | Auto-fill L days (every Saturday + Sunday of a month/year) |
| `lang.py` | EN/RO string table shared with the web app |
| `patients.json` | Remembered patient names (created automatically) |
| `settings.json` | Last export path (created automatically, not committed) |

Projects are saved wherever you choose via the file dialog; the Excel export
matches the phone/web version's layout exactly, so files are interchangeable.
