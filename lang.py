"""UI language: English / Romanian string table.

Pure data + lookup, no UI deps — shared by the desktop app and the web
bridge. Month VALUES (ianuarie…decembrie) and Excel file contents are
always Romanian; only interface text switches.
"""

import json

LANGS = ("en", "ro")

_current = "en"

STRINGS = {
    # ---- tabs ----
    "tab_build": {"en": "Build / Export", "ro": "Build / Export"},
    "tab_mark": {"en": "Mark appointment", "ro": "Introdu ședință"},
    "tab_patients": {"en": "Patients / Database", "ro": "Pacienți / Bază de date"},

    # ---- header ----
    "label_title": {"en": "Title (name):", "ro": "Titlu (nume):"},
    "ph_title": {"en": "e.g. POPOVICI EMANUEL", "ro": "ex. POPOVICI EMANUEL"},
    "label_month": {"en": "Month:", "ro": "Luna:"},
    "ph_month": {"en": "e.g. APRILIE", "ro": "ex. APRILIE"},
    "label_year": {"en": "Year:", "ro": "Anul:"},
    "label_days": {"en": "Days:", "ro": "Zile:"},
    "legend": {
        "en": "X = appointment  |  L = legal free day  |  C = free day  |  empty = not there",
        "ro": "X = ședință  |  L = zi liberă legală  |  C = zi liberă  |  gol = nu e prezent",
    },

    # ---- pattern ----
    "label_c_days": {"en": "C days (free):", "ro": "Zile C (libere):"},
    "ph_c_days": {"en": "e.g. 2, 5, 10, 13", "ro": "ex. 2, 5, 10, 13"},
    "label_l_days": {"en": "L days (legal):", "ro": "Zile L (legale):"},
    "ph_l_days": {"en": "e.g. 3, 4, 11, 12", "ro": "ex. 3, 4, 11, 12"},
    "btn_auto": {"en": "auto", "ro": "auto"},
    "pattern_hint": {
        "en": "same pattern for all patients",
        "ro": "același model pentru toți pacienții",
    },

    # ---- patient form ----
    "label_patient": {"en": "Patient name:", "ro": "Nume pacient:"},
    "ph_patient": {"en": "e.g. MOLAN MARIA", "ro": "ex. MOLAN MARIA"},
    "label_x_days": {"en": "Session days:", "ro": "Zile ședințe:"},
    "ph_x_days": {"en": "e.g. 1, 3, 5-7", "ro": "ex. 1, 3, 5-7"},
    "label_dec": {"en": "Decision date:", "ro": "Data decizie:"},
    "ph_dec": {"en": "e.g. 22.01", "ro": "ex. 22.01"},
    "label_zile": {"en": "Nr days:", "ro": "Nr. zile:"},
    "label_loc": {"en": "Locality:", "ro": "Localitate:"},
    "ph_loc": {"en": "e.g. VOINESTI", "ro": "ex. VOINESTI"},
    "btn_add": {"en": "Add patient", "ro": "Adaugă pacient"},
    "btn_update_sel": {"en": "Update selected", "ro": "Actualizează selectat"},
    "btn_remove_sel": {"en": "Remove selected", "ro": "Elimină selectat"},
    
    # ---- patient database ----
    "label_patient_name": {"en": "Patient name", "ro": "Nume pacient"},
    "label_localitate": {"en": "Locality", "ro": "Localitate"},
    "label_nr_zile": {"en": "Nr. days", "ro": "Nr. zile"},
    "label_dec_date": {"en": "Decision date", "ro": "Data decizie"},
    "label_date": {"en": "Date", "ro": "Data"},
    "label_diagnostic": {"en": "Diagnostic", "ro": "Diagnostic"},
    "label_objective": {"en": "Objective", "ro": "Obiectiv"},
    "label_evaluation": {"en": "Evaluation", "ro": "Evaluare"},
    "label_notes": {"en": "Notes", "ro": "Note"},
    "label_observation": {"en": "Observation", "ro": "Observație"},
    
    "btn_add_patient_db": {"en": "Add patient", "ro": "Adaugă pacient"},
    "btn_open_file": {"en": "Open file", "ro": "Deschide fișa"},
    "btn_delete_patient": {"en": "Delete patient", "ro": "Șterge pacient"},
    "btn_export_excel": {"en": "Export Excel", "ro": "Export Excel"},
    "btn_export_access": {"en": "Export Access", "ro": "Export Access"},
    "btn_edit_patient": {"en": "Edit patient", "ro": "Editează pacient"},
    "btn_save_all": {"en": "Save", "ro": "Salvează"},
    "btn_add_diagnosis": {"en": "Add diagnosis", "ro": "Adaugă diagnostic"},
    "btn_add_objective": {"en": "Add objective", "ro": "Adaugă obiectiv"},
    "btn_add_evaluation": {"en": "Add evaluation", "ro": "Adaugă evaluare"},
    "btn_add_observation": {"en": "Add observation", "ro": "Adaugă observație"},
    "btn_edit": {"en": "Edit", "ro": "Editează"},
    "btn_remove": {"en": "Remove", "ro": "Elimină"},
    "btn_ok": {"en": "OK", "ro": "OK"},
    
    "section_diagnoses": {"en": "Diagnoses", "ro": "Diagnostice"},
    "section_objectives": {"en": "Objectives", "ro": "Obiective"},
    "section_evaluations": {"en": "Evaluations", "ro": "Evaluări"},
    "section_observations": {"en": "Observations", "ro": "Observații"},
    
    "th_date": {"en": "Date", "ro": "Data"},
    "th_diagnostic": {"en": "Diagnostic", "ro": "Diagnostic"},
    "th_objective": {"en": "Objective", "ro": "Obiectiv"},
    "th_evaluation": {"en": "Evaluation", "ro": "Evaluare"},
    "th_notes": {"en": "Notes", "ro": "Note"},
    "th_observation": {"en": "Observation", "ro": "Observație"},
    "th_diag_count": {"en": "Diagnoses", "ro": "Diagnostice"},
    "th_obj_count": {"en": "Objectives", "ro": "Obiective"},
    "th_eval_count": {"en": "Evaluations", "ro": "Evaluări"},
    "th_obs_count": {"en": "Observations", "ro": "Observații"},
    
    "patient_page_title": {"en": "Patient File", "ro": "Fișă pacient"},
    
    "dlg_add_patient": {"en": "Add patient", "ro": "Adaugă pacient"},
    "dlg_edit_patient": {"en": "Edit patient", "ro": "Editează pacient"},
    "dlg_add_diagnosis": {"en": "Add diagnosis", "ro": "Adaugă diagnostic"},
    "dlg_edit_diagnosis": {"en": "Edit diagnosis", "ro": "Editează diagnostic"},
    "dlg_add_objective": {"en": "Add objective", "ro": "Adaugă obiectiv"},
    "dlg_edit_objective": {"en": "Edit objective", "ro": "Editează obiectiv"},
    "dlg_add_evaluation": {"en": "Add evaluation", "ro": "Adaugă evaluare"},
    "dlg_edit_evaluation": {"en": "Edit evaluation", "ro": "Editează evaluare"},
    "dlg_add_observation": {"en": "Add observation", "ro": "Adaugă observație"},
    "dlg_edit_observation": {"en": "Edit observation", "ro": "Editează observație"},
    
    "msg_select_patient": {"en": "Select a patient first.", "ro": "Selectați mai întâi un pacient."},
    "msg_select_item": {"en": "Select an item first.", "ro": "Selectați mai întâi un element."},
    "msg_required_fields": {"en": "Date and content are required.", "ro": "Data și conținutul sunt obligatorii."},
    "msg_saved": {"en": "Saved.", "ro": "Salvat."},
    "confirm_delete_patient": {"en": "Delete patient {name} and all their data?", "ro": "Ștergeți pacientul {name} și toate datele sale?"},
    "confirm_remove_item": {"en": "Remove this item?", "ro": "Eliminați acest element?"},
    
    "app_name": {"en": "Patient Database", "ro": "Bază de date pacienți"},

    # ---- table headings (screen only; Excel stays Romanian) ----
    "th_nr": {"en": "NR.", "ro": "NR."},
    "th_patient": {"en": "PATIENT", "ro": "PACIENT"},
    "th_x": {"en": "SESSION DAYS", "ro": "ZILE ȘEDINȚE"},
    "th_count": {"en": "COUNT", "ro": "COUNT"},
    "th_dec": {"en": "DECISION DATE", "ro": "DATA DECIZIE"},
    "th_zile": {"en": "NR DAYS", "ro": "NR. ZILE"},
    "th_loc": {"en": "LOCALITY", "ro": "LOCALITATE"},

    # ---- bottom buttons ----
    "btn_save": {"en": "Save project...", "ro": "Salvează proiectul..."},
    "btn_load": {"en": "Load project...", "ro": "Încarcă proiectul..."},
    "btn_clear": {"en": "Clear all", "ro": "Golește tot"},
    "btn_export": {"en": "Export to Excel...", "ro": "Exportă în Excel..."},
    "btn_cancel": {"en": "Cancel", "ro": "Anulează"},

    # ---- status bar ----
    "status_counts": {
        "en": "{n} patients | {k} known names",
        "ro": "{n} pacienți | {k} nume cunoscute",
    },
    "overview_count": {
        "en": "{n} of {total} patients",
        "ro": "{n} din {total} pacienți",
    },
    "overview_count_all": {
        "en": "{n} patients",
        "ro": "{n} pacienți",
    },
    "empty_no_patients": {
        "en": "No patients yet. Use “+ New Patient” to add the first one.",
        "ro": "Niciun pacient încă. Folosiți „+ New Patient” pentru a adăuga primul.",
    },
    "empty_no_match": {
        "en": "No patient matches “{q}”.",
        "ro": "Niciun pacient nu corespunde „{q}”.",
    },
    "hint_list_keys": {
        "en": "Tip: ↑/↓ moves between patients, Enter opens the file.",
        "ro": "Sugestie: ↑/↓ schimbă pacientul, Enter deschide fișa.",
    },
    "status_list_error": {
        "en": " | name list problem: {err}",
        "ro": " | problemă listă nume: {err}",
    },
    "status_saved": {"en": "Saved: {path}", "ro": "Salvat: {path}"},
    "status_loaded": {"en": "Loaded: {path}", "ro": "Încărcat: {path}"},
    "status_kept_sheet": {
        "en": "Kept existing sheet {sheet}",
        "ro": "Foaia existentă {sheet} păstrată",
    },
    "status_exported_csv": {"en": "CSV export successful", "ro": "Export CSV reușit"},
    "status_exported_word": {"en": "Word export successful", "ro": "Export Word reușit"},
    "msg_backup_created": {"en": "Backup created and verified ({n} patients):\\n{path}", "ro": "Backup creat și verificat ({n} pacienți):\\n{path}"},
    "msg_backup_warn": {"en": "Backup created but verification failed:\\n{info}", "ro": "Backup creat dar verificarea a eșuat:\\n{info}"},

    # ---- generic errors (backend/shared) ----
    "err_days_whole": {
        "en": "Days must be a whole number between 1 and 31.",
        "ro": "Zilele trebuie să fie un număr întreg între 1 și 31.",
    },
    "err_year_whole": {
        "en": "Year must be a whole number like 2026.",
        "ro": "Anul trebuie să fie un număr întreg, ex. 2026.",
    },
    "err_year_range": {
        "en": "Year must be between 2000 and 2100.",
        "ro": "Anul trebuie să fie între 2000 și 2100.",
    },
    "err_range_reversed": {
        "en": "Invalid range '{part}': start is bigger than end.",
        "ro": "Interval nevalid '{part}': începutul e mai mare decât sfârșitul.",
    },
    "err_range_long": {
        "en": "Range too long: '{part}'.",
        "ro": "Interval prea lung: '{part}'.",
    },
    "err_day_value": {
        "en": "Invalid day value: '{part}'.",
        "ro": "Valoare zi nevalidă: '{part}'.",
    },
    "err_days_between": {
        "en": "Days must be between 1 and {limit}.",
        "ro": "Zilele trebuie să fie între 1 și {limit}.",
    },
    "err_days_list": {
        "en": "Days must be a list of numbers or a text like '1, 3, 5-7'.",
        "ro": "Zilele trebuie să fie o listă de numere sau text de tipul '1, 3, 5-7'.",
    },
    "err_project_object": {
        "en": "Project must be a JSON object.",
        "ro": "Proiectul trebuie să fie un obiect JSON.",
    },
    "err_missing_field": {
        "en": "Missing field: {field}",
        "ro": "Lipsește câmpul: {field}",
    },
    "err_c_l_lists": {
        "en": "C days and L days must be lists.",
        "ro": "Zilele C și L trebuie să fie liste.",
    },
    "err_patients_list": {
        "en": "Patients must be a list.",
        "ro": "Pacienții trebuie să fie o listă.",
    },
    "err_patient_object": {
        "en": "Each patient must be an object.",
        "ro": "Fiecare pacient trebuie să fie un obiect.",
    },
    "err_json_invalid": {
        "en": "Not a valid JSON file: {exc}",
        "ro": "Nu e un fișier JSON valid: {exc}",
    },
    "err_patients_array": {
        "en": "Patients list must be a JSON array of names.",
        "ro": "Lista de pacienți trebuie să fie un array JSON de nume.",
    },
    "err_add_patient_first": {
        "en": "Add at least one patient before exporting.",
        "ro": "Adaugă cel puțin un pacient înainte de export.",
    },
    "err_excel_invalid": {
        "en": "Not a valid Excel file: {path}\n{exc}",
        "ro": "Nu e un fișier Excel valid: {path}\n{exc}",
    },
    "err_month_empty": {
        "en": "Month is empty — use Romanian names (ianuarie…decembrie) or a number like 9.",
        "ro": "Luna e goală — folosește ianuarie…decembrie sau un număr ca 9.",
    },
    "err_month_number": {
        "en": "Invalid month number: {text}.",
        "ro": "Număr lună nevalid: {text}.",
    },
    "err_month_unknown": {
        "en": "Unknown month '{month}' — use Romanian names (ianuarie…decembrie) or a number like 9.",
        "ro": "Lună necunoscută '{month}' — folosește ianuarie…decembrie sau un număr ca 9.",
    },
    "err_patient_name_required": {
        "en": "Patient name is required.",
        "ro": "Numele pacientului e obligatoriu.",
    },
    "err_patient_name_empty": {
        "en": "Patient name is empty.",
        "ro": "Numele pacientului e gol.",
    },
    "err_day_whole": {
        "en": "Day must be a whole number like 30.",
        "ro": "Ziua trebuie să fie un număr întreg, ex. 30.",
    },
    "err_day_range": {
        "en": "Day must be between 1 and {last} for {sheet}.",
        "ro": "Ziua trebuie să fie între 1 și {last} pentru {sheet}.",
    },
    "err_date_format": {
        "en": "Date must look like 30.04.2026",
        "ro": "Data trebuie să arate ca 30.04.2026",
    },

    # ---- desktop popups ----
    "info_select_patient": {
        "en": "Select a patient in the table first.",
        "ro": "Selectează mai întâi un pacient din tabel.",
    },
    "confirm_clear": {
        "en": "Clear everything (header, pattern, all patients)?",
        "ro": "Golește tot (antetul, modelul, toți pacienții)?",
    },
    "err_cannot_save": {
        "en": "Cannot save project:\n{exc}",
        "ro": "Nu pot salva proiectul:\n{exc}",
    },
    "err_cannot_load": {
        "en": "Cannot load project:\n{exc}",
        "ro": "Nu pot încărca proiectul:\n{exc}",
    },
    "err_export_failed": {
        "en": "Export failed:\n{exc}",
        "ro": "Exportul a eșuat:\n{exc}",
    },
    "info_exported": {
        "en": "Exported sheet {sheet}:\n{path}",
        "ro": "Exportat foaia {sheet}:\n{path}",
    },

    # ---- file dialogs ----
    "dlg_save_project": {"en": "Save project", "ro": "Salvează proiectul"},
    "dlg_load_project": {"en": "Load project", "ro": "Încarcă proiectul"},
    "ft_json": {"en": "JSON project", "ro": "Proiect JSON"},
    "ft_excel": {"en": "Excel file", "ro": "Fișier Excel"},
    "ft_all": {"en": "All files", "ro": "Toate fișierele"},
    "dlg_select_workbook": {
        "en": "Select workbook to update",
        "ro": "Selectează registrul de actualizat",
    },
    "dlg_create_workbook": {
        "en": "Create new Excel workbook",
        "ro": "Creează registru Excel nou",
    },
    "dlg_select_excel": {
        "en": "Select Excel workbook",
        "ro": "Selectează registru Excel",
    },

    # ---- export mode dialog ----
    "dlg_export_title": {"en": "Export to Excel", "ro": "Exportă în Excel"},
    "dlg_export_question": {
        "en": "Update an existing workbook, or create a new one?",
        "ro": "Actualizează un registru existent sau creează unul nou?",
    },
    "btn_update_workbook": {
        "en": "Update existing workbook...",
        "ro": "Actualizează registrul existent...",
    },
    "btn_create_workbook": {
        "en": "Create new workbook...",
        "ro": "Creează registru nou...",
    },

    # ---- sheet replace confirm ----
    "confirm_sheet_replace": {
        "en": ("Sheet {sheet} already exists in:\n{path}\n\n"
               "Replace it with the new data?\n\n"
               "Yes = replace the old sheet\n"
               "No = keep the existing sheet (export cancelled)"),
        "ro": ("Foaia {sheet} există deja în:\n{path}\n\n"
               "O înlocuiești cu datele noi?\n\n"
               "Da = înlocuiește vechea foaie\n"
               "Nu = păstrează foaia existentă (export anulat)"),
    },

    # ---- mark tab (Introdu ședință) ----
    "mark_desc": {
        "en": ("Mark an appointment (X) for a patient on a date in the Excel "
               "workbook. The patient is added to the month sheet if missing."),
        "ro": ("Marchează o ședință (X) pentru un pacient la o dată în "
               "registrul Excel. Pacientul este adăugat în foaia lunii dacă lipsește."),
    },
    "mark_ph_name": {"en": "e.g. STOICA FLORIN", "ro": "ex. STOICA FLORIN"},
    "mark_date_label": {"en": "Date:", "ro": "Data:"},
    "mark_btn": {"en": "Mark appointment", "ro": "Marchează ședința"},
    "mark_no_workbook": {
        "en": "No workbook selected — export one first.",
        "ro": "Niciun registru selectat — exportă unul mai întâi.",
    },
    "mark_failed": {"en": "Failed: {exc}", "ro": "Eșec: {exc}"},
    "mark_already": {
        "en": "Already marked: {who} on {sheet}",
        "ro": "Deja marcat: {who} pe {sheet}",
    },
    "mark_added": {
        "en": "Added {who} + X on {sheet}",
        "ro": "Adăugat {who} + X pe {sheet}",
    },
    "mark_marked": {
        "en": "Marked X for {who} on {sheet}",
        "ro": "Marcat X pentru {who} pe {sheet}",
    },

    # ---- web: chrome / boot ----
    "web_pill_loading": {"en": "loading", "ro": "se încarcă"},
    "web_status_boot1": {
        "en": "Loading Python runtime…",
        "ro": "Se încarcă runtime-ul Python…",
    },
    "web_status_boot2": {"en": "Starting Python…", "ro": "Se pornește Python…"},
    "web_status_boot3": {
        "en": "Loading Excel engine (openpyxl)…",
        "ro": "Se încarcă motorul Excel (openpyxl)…",
    },
    "web_status_boot4": {
        "en": "Loading app logic…",
        "ro": "Se încarcă logica aplicației…",
    },
    "web_status_ready": {"en": "Ready", "ro": "Gata"},
    "web_status_ready_offline": {"en": "Ready — offline", "ro": "Gata — offline"},
    "web_status_load_failed": {
        "en": "Load failed: {err} — tap to retry",
        "ro": "Încărcarea a eșuat: {err} — atinge pentru reîncercare",
    },
    "web_h2_header": {"en": "Header", "ro": "Antet"},
    "web_h2_pattern": {"en": "Pattern", "ro": "Model"},
    "web_h2_patients": {"en": "Patients", "ro": "Pacienți"},
    "web_form_edit": {"en": "Edit patient", "ro": "Editează pacient"},
    "web_empty": {
        "en": "No patients yet. Add one above.",
        "ro": "Niciun pacient încă. Adaugă unul mai sus.",
    },
    "web_mark_small": {
        "en": "mark an X by date in the workbook",
        "ro": "marchează un X după dată în registru",
    },
    "web_label_date": {"en": "Date", "ro": "Data"},
    "web_btn_xlsx": {"en": "⬇ Export Excel (.xlsx)", "ro": "⬇ Exportă Excel (.xlsx)"},
    "web_btn_json_out": {"en": "Export project (.json)", "ro": "Exportă proiect (.json)"},
    "web_btn_json_in": {"en": "Import project (.json)", "ro": "Importă proiect (.json)"},
    "web_btn_xlsx_in": {"en": "Load workbook (.xlsx)", "ro": "Încarcă registru (.xlsx)"},
    "web_btn_update": {"en": "Update", "ro": "Actualizează"},
    "web_footer": {
        "en": "Python runs locally in your browser — your data never leaves this device. Works offline after the first load.",
        "ro": "Rulează local în browser — datele tale nu părăsesc acest dispozitiv. Funcționează offline după prima încărcare.",
    },
    "web_modal_title": {"en": "Export to Excel", "ro": "Exportă în Excel"},
    "web_modal_hint": {
        "en": ("Update the workbook saved in this browser, or create a "
               "brand-new one. The file is always downloaded to your device."),
        "ro": ("Actualizează registrul salvat în acest browser sau creează unul "
               "nou. Fișierul se descarcă mereu pe dispozitiv."),
    },
    "web_btn_ex_update": {
        "en": "Update existing workbook…",
        "ro": "Actualizează registrul existent…",
    },
    "web_btn_ex_new": {
        "en": "Create new workbook…",
        "ro": "Creează registru nou…",
    },
    "web_lang_label": {"en": "Language", "ro": "Limbă"},

    # ---- web: toasts / confirms / dynamic ----
    "web_toast_patient_added": {"en": "Patient added.", "ro": "Pacient adăugat."},
    "web_toast_patient_updated": {"en": "Patient updated.", "ro": "Pacient actualizat."},
    "web_toast_patient_removed": {"en": "Patient removed.", "ro": "Pacient eliminat."},
    "web_confirm_remove": {"en": "Remove {name}?", "ro": "Elimini pe {name}?"},
    "web_toast_x_days": {"en": "X days: {err}", "ro": "Zile X: {err}"},
    "web_label_c_field": {"en": "C days", "ro": "Zile C"},
    "web_label_l_field": {"en": "L days", "ro": "Zile L"},
    "web_confirm_sheet": {
        "en": ("Sheet {sheet} already exists in the stored workbook.\n\n"
               "Replace it with the new data?"),
        "ro": ("Foaia {sheet} există deja în registrul salvat.\n\n"
               "O înlocuiești cu datele noi?"),
    },
    "web_toast_exported": {
        "en": "Exported sheet {sheet} — file downloaded.",
        "ro": "Exportat foaia {sheet} — fișier descărcat.",
    },
    "web_toast_no_workbook_update": {
        "en": ("No workbook saved in this browser yet — use "
               "“Create new workbook” or “Load workbook (.xlsx)” first."),
        "ro": ("Niciun registru salvat în acest browser — folosește "
               "«Creează registru nou» sau «Încarcă registru (.xlsx)» mai întâi."),
    },
    "web_toast_still_loading": {
        "en": "Still loading — try again in a moment.",
        "ro": "Se încarcă încă — încearcă din nou într-un moment.",
    },
    "web_toast_cannot_read": {
        "en": "Cannot read workbook: {err}",
        "ro": "Nu pot citi registrul: {err}",
    },
    "web_toast_loaded_sheets": {
        "en": "Workbook loaded ({n} sheets).",
        "ro": "Registru încărcat ({n} foi).",
    },
    "web_toast_load_failed": {
        "en": "Load failed: {err}",
        "ro": "Încărcarea a eșuat: {err}",
    },
    "web_toast_date_required": {
        "en": "Date is required, e.g. 30.04.2026.",
        "ro": "Data e obligatorie, ex. 30.04.2026.",
    },
    "web_toast_no_workbook_mark": {
        "en": ("No workbook in this browser yet — export a new one first "
               "(or use “Load workbook (.xlsx)”)."),
        "ro": ("Niciun registru în acest browser — exportă unul nou mai întâi "
               "(sau folosește «Încarcă registru (.xlsx)»)."),
    },
    "web_suffix_downloaded": {
        "en": " — file downloaded.",
        "ro": " — fișier descărcat.",
    },
    "web_toast_project_exported": {
        "en": "Project file exported.",
        "ro": "Fișier proiect exportat.",
    },
    "web_toast_import_failed": {
        "en": "Import failed: {err}",
        "ro": "Importul a eșuat: {err}",
    },
    "web_confirm_clear": {
        "en": "Clear header, pattern and all patients?",
        "ro": "Golește antetul, modelul și toți pacienții?",
    },
    "web_lang_en": {"en": "English", "ro": "English"},
    "ui_theme_label": {"en": "Theme:", "ro": "Temă:"},

    # ---- UI (desktop) ----
    "ui_section_diagnostic": {"en": "Diagnostic", "ro": "Diagnostic"},
    "ui_section_objective": {"en": "Objective", "ro": "Obiectiv"},
    "ui_section_evaluation": {"en": "Evaluation", "ro": "Evaluare"},
    "ui_section_observation": {"en": "Observation", "ro": "Observație"},
    "ui_available_fields": {"en": "Available fields", "ro": "Câmpuri disponibile"},
    "ui_selected_in_order": {"en": "Selected (in order)", "ro": "Selectate (în ordine)"},
    "ui_search_patients": {"en": "Search patients...", "ro": "Caută pacienți..."},
    "ui_new_patient": {"en": "+ New Patient", "ro": "+ Pacient nou"},
    "ui_restore": {"en": "Restore", "ro": "Restaurează"},
    "ui_restore_all": {"en": "Restore all", "ro": "Restaurează tot"},
    "ui_purge": {"en": "Purge", "ro": "Șterge definitiv"},
    "ui_empty_trash": {"en": "Empty", "ro": "Golește"},
    "ui_open_trash": {"en": "Open Trash (deleted patients)", "ro": "Deschide coș (pacienți șterși)"},
    "ui_backup_now": {"en": "Backup now", "ro": "Backup acum"},
    "ui_restore_backup": {"en": "Restore...", "ro": "Restaurează..."},
    "ui_import": {"en": "Import...", "ro": "Importă..."},
    "ui_ui_scale": {"en": "UI scale:", "ro": "Scalare UI:"},
    "ui_interface_theme": {"en": "Interface theme:", "ro": "Temă interfață:"},
    "ui_theme_classic": {"en": "Classic", "ro": "Clasic"},
    "ui_theme_medidash": {"en": "MediDashboard", "ro": "MediDashboard"},
    "ui_light": {"en": "Light", "ro": "Luminos"},
    "ui_dark": {"en": "Dark", "ro": "Întunecat"},
    "ui_language": {"en": "Language:", "ro": "Limbă:"},
    "ui_data": {"en": "Data:", "ro": "Date:"},
    "ui_trash": {"en": "Trash (deleted)", "ro": "Coș (șterși)"},
    "ui_settings": {"en": "Settings", "ro": "Setări"},
    "ui_save_as": {"en": "Save as", "ro": "Salvează ca"},
    "ui_backup": {"en": "Backup", "ro": "Backup"},
    "ui_patients": {"en": "Patients", "ro": "Pacienți"},
    "ui_new": {"en": "New", "ro": "Nou"},
    "ui_name": {"en": "Name", "ro": "Nume"},
    "ui_locality": {"en": "Locality", "ro": "Localitate"},
    "ui_deleted_at": {"en": "Deleted at", "ro": "Șters la"},
    "ui_choose_format": {"en": "Choose format:", "ro": "Alege formatul:"},
    "ui_export": {"en": "Export", "ro": "Exportă"},
    "ui_export_excel": {"en": "Excel (.xlsx)", "ro": "Excel (.xlsx)"},
    "ui_export_csv": {"en": "CSV / Access", "ro": "CSV / Access"},
    "ui_export_pdf": {"en": "PDF", "ro": "PDF"},
    "ui_export_word": {"en": "Word (.doc)", "ro": "Word (.doc)"},
    "ui_clear_search": {"en": "Clear search", "ro": "Șterge căutarea"},
    "ui_sort": {"en": "Sort patients", "ro": "Sortează pacienții"},
    "ui_open_file": {"en": "Open File", "ro": "Deschide fișa"},
    "ui_edit": {"en": "Edit", "ro": "Editează"},
    "ui_delete": {"en": "Delete", "ro": "Șterge"},
    "ui_copy_name": {"en": "Copy name", "ro": "Copiază numele"},
    "ui_print_pdf": {"en": "Print / PDF", "ro": "Tipărește / PDF"},
    "ui_save_record": {"en": "Save Patient Record", "ro": "Salvează fișa pacientului"},
    "ui_cancel": {"en": "Cancel", "ro": "Anulează"},
    "ui_attach_file": {"en": "Attach file", "ro": "Atașează fișier"},
    "ui_open": {"en": "Open", "ro": "Deschide"},
    "ui_refresh": {"en": "Refresh", "ro": "Reîmprospătează"},
    "ui_clear_history": {"en": "Clear history", "ro": "Șterge istoricul"},
    "ui_last_modified": {"en": "Last modified:", "ro": "Ultima modificare:"},
    "ui_last_activity": {"en": "Last Activity:", "ro": "Ultima activitate:"},
    "ui_select_patient_file": {"en": "Select a patient to view their file", "ro": "Selectați un pacient pentru a-i vedea fișa"},
    "ui_no_patients": {"en": "No patients yet. Use “+ New Patient” to add the first one.", "ro": "Niciun pacient încă. Folosiți „+ Pacient nou” pentru a adăuga primul."},
    "ui_no_match": {"en": "No patient matches “{q}”.", "ro": "Niciun pacient nu corespunde „{q}”."},
    "ui_count_of": {"en": "{n} of {total} patients", "ro": "{n} din {total} pacienți"},
    "ui_count_all": {"en": "{n} patients", "ro": "{n} pacienți"},
    "ui_hint_keys": {"en": "Tip: ↑/↓ moves between patients, Enter opens the file.", "ro": "Sugestie: ↑/↓ schimbă pacientul, Enter deschide fișa."},
    "ui_keyboard_shortcuts": {"en": "Keyboard shortcuts", "ro": "Scurtături tastatură"},
    "ui_about": {"en": "About", "ro": "Despre"},
    "ui_close": {"en": "Close", "ro": "Închide"},
    "ui_code": {"en": "Code", "ro": "Cod"},
    "ui_dob": {"en": "DOB", "ro": "Data nașterii"},
    "ui_sex": {"en": "Sex", "ro": "Sex"},
    "ui_diagnosis": {"en": "Diagnosis", "ro": "Diagnostic"},
    "ui_photo": {"en": "Photo", "ro": "Fotografie"},
    "ui_name_required": {"en": "Patient name is required.", "ro": "Numele pacientului este obligatoriu."},
    "ui_invalid_date": {"en": "Invalid date (use DD.MM.YYYY).", "ro": "Dată invalidă (folosiți ZZ.LL.AAAA)."},
    "ui_not_saved_yet": {"en": "Not saved yet", "ro": "Nesalvat încă"},
    "ui_auto": {"en": "auto", "ro": "auto"},
    "ui_deleted": {"en": "Deleted", "ro": "Șters"},
    "ui_ctrl_z_undo": {"en": "Ctrl+Z to undo", "ro": "Ctrl+Z pentru anulare"},
    "ui_export_excel_ok": {"en": "Export Excel successful", "ro": "Export Excel reușit"},
    "ui_export_word_ok": {"en": "Export Word successful", "ro": "Export Word reușit"},
    "ui_export_csv_ok": {"en": "Export CSV successful", "ro": "Export CSV reușit"},
    "ui_backup_created": {"en": "Backup created and verified ({n} patients):\\n{path}", "ro": "Backup creat și verificat ({n} pacienți):\\n{path}"},
    "ui_backup_warn": {"en": "Backup created but verification failed:\\n{info}", "ro": "Backup creat dar verificarea a eșuat:\\n{info}"},
    "ui_imported": {"en": "Imported {n} patients.", "ro": "Importați {n} pacienți."},
    "ui_file_attached": {"en": "File attached.", "ro": "Fișier atașat."},
    "ui_file_not_found": {"en": "File not found.", "ro": "Fișierul nu a fost găsit."},
    "ui_select_attachment": {"en": "Select an attachment.", "ro": "Selectați un atașament."},
    "ui_select_patient_first": {"en": "Select a patient first.", "ro": "Selectați mai întâi un pacient."},
    "ui_deleted_patient": {"en": "Deleted patient '{name}'. Press Ctrl+Z to undo.", "ro": "Pacient șters „{name}”. Apăsați Ctrl+Z pentru anulare."},
    "ui_restore_patient": {"en": "Undo: patient restored.", "ro": "Anulare: pacient restaurat."},
    "ui_empty_pdf": {"en": "Empty PDF.", "ro": "PDF gol."},
    "ui_no_preview": {"en": "No preview available.", "ro": "Previzualizare indisponibilă."},
    "ui_all_files": {"en": "All files", "ro": "Toate fișierele"},
}


def set_language(code):
    global _current
    _current = code if code in LANGS else "en"


def get_language():
    return _current


def t(key, **fmt):
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry.get("en") or key
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def strings_json(code=None):
    """Whole string table for one language (for the web frontend)."""
    code = code if code in LANGS else "en"
    table = {}
    for key, entry in STRINGS.items():
        table[key] = entry.get(code) or entry.get("en") or key
    return json.dumps(table, ensure_ascii=False)
