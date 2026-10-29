"""Frontend: customtkinter GUI with Patient Database."""
import json
import os
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

import lang
import db
import theme
from patient_panel import PatientFilePanel

APP_NAME = "Patient Database"

import unicodedata

def _norm(s):
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

LANG_LABELS = {"en": "English", "ro": "Română"}


def settings_file():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def load_settings():
    try:
        with open(settings_file(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        with open(settings_file(), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except OSError:
        pass


def load_language():
    code = str(load_settings().get("language", "en"))
    return code if code in lang.LANGS else "en"


def save_language(code):
    data = load_settings()
    data["language"] = code
    save_settings(data)



def _initials(name):
    parts = (name or "").split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[-1][:1]).upper()

class App(ctk.CTk):
    def __init__(self, patients_file=None):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        lang.set_language(load_language())
        self.title(lang.t("app_name"))
        self.minsize(1100, 700)
        # Restore window geometry / theme from settings
        try:
            settings = load_settings()
            geom = settings.get("geometry")
            if geom:
                self.geometry(geom)
            else:
                self.geometry("1200x800")
            mode = settings.get("appearance", "Light")
            ctk.set_appearance_mode(mode)
        except Exception:
            self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        # Initialize database
        db.init_db()

        self.patients_file = patients_file
        self.list_error = None
        try:
            self.known_patients = db.get_patient_names()
        except Exception as exc:
            self.known_patients = []
            self.list_error = str(exc)

        self.patient_pages = {}
        _st = load_settings()
        self.sort_by = _st.get("sort_by", "name")
        self.sort_dir = _st.get("sort_dir", "asc")
        self.search_scope = "everything"
        self.selected_patient_id = None
        self._current_panel = None
        self.patient_panels = {}

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # Menu bar
        self._build_menubar()

        # Top header bar
        self._build_header_bar()

        # Sidebar
        self._build_sidebar()

        # Content: overview (left) + file (right)
        self._build_content()

        self.refresh_patients_db()
        self._auto_backup()
        # Keyboard shortcuts
        self.bind("<Control-n>", lambda e: self._add_patient_db())
        self.bind("<Control-f>", lambda e: (self.search_entry.focus_set() if hasattr(self, "search_entry") else None, "break"))

    def _on_app_close(self):
        try:
            data = load_settings()
            data["geometry"] = self.geometry()
            save_settings(data)
        except Exception:
            pass
        self.destroy()

    def _build_menubar(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save as...", command=self._save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Backup now", command=self._backup_now)
        file_menu.add_command(label="Restore backup...", command=self._restore_backup)
        file_menu.add_separator()
        file_menu.add_command(label="Import...", command=self._import_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_app_close)
        menubar.add_cascade(label="File", menu=file_menu)
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Add patient", command=self._add_patient_db)
        edit_menu.add_command(label="Open patient file", command=self._open_patient_file)
        edit_menu.add_command(label="Delete patient", command=self._delete_patient_db)
        edit_menu.add_separator()
        edit_menu.add_command(label="Trash (deleted)", command=self._show_trash)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle theme", command=self._toggle_theme)
        lang_submenu = tk.Menu(view_menu, tearoff=0)
        for code, label in LANG_LABELS.items():
            lang_submenu.add_command(label=label, command=lambda c=code: self._on_language_change(c == "ro" and "Română" or "English"))
        view_menu.add_cascade(label="Language", menu=lang_submenu)
        menubar.add_cascade(label="View", menu=view_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo(lang.t("app_name"), "Patient Database\nSQLite-backed patient records."))
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _on_language_change(self, choice):
        code = "ro" if choice == "Română" else "en"
        if code == lang.get_language():
            return
        lang.set_language(code)
        save_language(code)
        self.refresh_patients_db()
        self.title(lang.t("app_name"))

    def _build_header_bar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=theme.PADDING, pady=(10, 6))
        bar.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(brand, text="Medi", font=theme.FONT_TITLE, text_color=theme.TEXT).pack(side="left")
        ctk.CTkLabel(brand, text="Dashboard Pro", font=theme.FONT_TITLE, text_color=theme.ACCENT).pack(side="left")

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(right, text="Theme", width=70, command=self._toggle_theme).pack(side="left", padx=2)
        self.lang_menu = ctk.CTkOptionMenu(right, values=list(LANG_LABELS.values()), width=95, command=self._on_language_change)
        self.lang_menu.set(LANG_LABELS.get(lang.get_language(), "English"))
        self.lang_menu.pack(side="left", padx=2)

    def _build_sidebar(self):
        side = ctk.CTkFrame(self, width=theme.SIDEBAR_W, fg_color=theme.SIDEBAR_BG, corner_radius=0)
        side.grid(row=1, column=0, sticky="nsw", padx=(8, 0), pady=8)
        side.grid_propagate(False)
        self._sidebar = side

        logo = ctk.CTkLabel(side, text="\u2695", font=("Segoe UI", 26), text_color=theme.ACCENT)
        logo.pack(pady=(12, 18))

        self._nav_buttons = {}
        items = [("patients", "\u2630", "Patients", self._nav_patients, ("Segoe UI", 16)),
                 ("new", "\u2795", "New", self._add_patient_db, ("Segoe UI", 16)),
                 ("saveas", "\u2912", "Save as", self._save_as, ("Segoe UI", 16)),
                 ("backup", "\u21BB", "Backup", self._backup_now, ("Segoe UI", 16)),
                 ("trash", "\U0001F5D1", "Trash", self._show_trash, ("Segoe UI Emoji", 16)),
                 ("settings", "\u2699", "Settings", self._nav_settings, ("Segoe UI", 16))]
        for key, glyph, tip, cmd, font in items:
            btn = ctk.CTkButton(side, text=glyph, width=44, height=44, corner_radius=12,
                                fg_color="transparent", text_color=theme.TEXT, hover_color=theme.SIDEBAR_ACTIVE,
                                font=font, command=cmd)
            btn.pack(pady=4)
            self._nav_buttons[key] = btn
        self._set_nav_active("patients")

    def _set_nav_active(self, key):
        for k, b in getattr(self, "_nav_buttons", {}).items():
            b.configure(fg_color=theme.SIDEBAR_ACTIVE if k == key else "transparent")

    def _nav_patients(self):
        self._set_nav_active("patients")

    def _nav_settings(self):
        self._set_nav_active("settings")
        dlg = SettingsDialog(self)
        self.wait_window(dlg)

    def _build_content(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        content.grid_columnconfigure(0, weight=0)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)
        self._content = content

        self.overview_panel = ctk.CTkFrame(content, fg_color=theme.PANEL, corner_radius=theme.PANEL_RADIUS,
                                           border_width=1, border_color=theme.BORDER)
        self.overview_panel.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        self.overview_panel.grid_propagate(False)
        self.overview_panel.configure(width=340)
        self._build_overview(self.overview_panel)

        self.file_host = ctk.CTkFrame(content, fg_color=theme.PANEL, corner_radius=theme.PANEL_RADIUS,
                                      border_width=1, border_color=theme.BORDER)
        self.file_host.grid(row=0, column=1, sticky="nsew")
        self.file_host.grid_columnconfigure(0, weight=1)
        self.file_host.grid_rowconfigure(0, weight=1)
        self._show_placeholder()

    def _build_overview(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(parent, text="Patient Overview", font=theme.FONT_TITLE, text_color=theme.TEXT).grid(
            row=0, column=0, sticky="w", padx=theme.PADDING, pady=(theme.PADDING, 6))

        search_frame = ctk.CTkFrame(parent, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=theme.PADDING, pady=(0, 6))
        search_frame.grid_columnconfigure(1, weight=1)
        self.search_scope = ctk.CTkOptionMenu(search_frame, values=["Name", "Everything"], width=95,
                                             command=lambda v: (setattr(self, "search_scope", v.lower()), self.refresh_patients_db()))
        self.search_scope.set("Everything")
        self.search_scope.pack(side="left", padx=(0, 6))
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search patients...")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_patients_db())
        ctk.CTkButton(search_frame, text="\u00d7", width=26, command=self._clear_search).pack(side="left", padx=2)

        self.card_list = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.card_list.grid(row=2, column=0, sticky="nsew", padx=theme.PADDING, pady=(0, 6))
        self.card_list.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(parent, text="+ New Patient", height=36, fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK,
                      font=theme.FONT_BOLD, command=self._add_patient_db).grid(
            row=3, column=0, sticky="ew", padx=theme.PADDING, pady=(6, theme.PADDING))

    def _show_placeholder(self):
        for w in self.file_host.winfo_children():
            w.destroy()
        lbl = ctk.CTkLabel(self.file_host, text="Select a patient to view their file",
                           font=theme.FONT_SUB, text_color=theme.MUTED)
        lbl.place(relx=0.5, rely=0.5, anchor="center")

    def refresh_patients_db(self):
        for w in self.card_list.winfo_children():
            w.destroy()
        try:
            patients = db.get_all_patients(sort_by=self.sort_by, sort_dir=self.sort_dir)
            search_raw = self.search_entry.get() if hasattr(self, "search_entry") else ""
            search = _norm(search_raw)
            scope = getattr(self, "search_scope", "everything")
            scope = scope.lower() if isinstance(scope, str) else "everything"
            shown = 0
            for p in patients:
                diag_text = p.get('diagnostic', '') or ''
                first_line = diag_text.split(chr(10))[0] if diag_text else ''
                if scope == "name":
                    haystack = _norm(p.get('name', ''))
                else:
                    haystack = _norm(" ".join([str(p.get('name','')), str(p.get('localitate','')), diag_text,
                                               p.get('objective','') or '', p.get('evaluation','') or '',
                                               p.get('observation','') or '']))
                if search and search not in haystack:
                    continue
                shown += 1
                self._build_patient_card(p, first_line, (p.get('id') == self.selected_patient_id))
            if hasattr(self, "status_label"):
                pass
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _build_patient_card(self, p, first_line, selected):
        card = ctk.CTkFrame(self.card_list, fg_color=theme.SELECTED if selected else theme.PANEL,
                            corner_radius=theme.CARD_RADIUS, border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=4)
        card.grid_columnconfigure(1, weight=1)

        av = ctk.CTkLabel(card, text=_initials(p.get('name','')), width=36, height=36,
                          corner_radius=18, fg_color=theme.ACCENT, text_color="white",
                          font=ctk.CTkFont(size=12, weight="bold"))
        av.grid(row=0, column=0, rowspan=2, padx=10, pady=8)

        name_lbl = ctk.CTkLabel(card, text=p.get('name',''), font=theme.FONT_BOLD, text_color=theme.TEXT, anchor="w")
        name_lbl.grid(row=0, column=1, sticky="w", pady=(8, 0))

        meta = ctk.CTkLabel(card, text=p.get('localitate','') or "\u2014", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        meta.grid(row=1, column=1, sticky="w")

        preview = ctk.CTkLabel(card, text=(first_line[:50] + ("..." if len(first_line) > 50 else "")) or "No diagnostic",
                               font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        preview.grid(row=2, column=1, sticky="w", pady=(2, 8))

        if selected:
            open_btn = ctk.CTkButton(card, text="Open \u203A", width=80, height=24, corner_radius=8,
                                     fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK, font=theme.FONT_SMALL,
                                     command=lambda pid=p['id']: self._open_patient_by_id(pid))
            open_btn.grid(row=0, column=2, rowspan=3, padx=10)

        for w in (card, av, name_lbl, meta, preview):
            w.bind("<Button-1>", lambda e, pid=p['id']: self._open_patient_by_id(pid))
            w.bind("<Button-3>", lambda e, pid=p['id']: self._card_context(e, pid))

    def _card_context(self, event, pid):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Edit patient", command=lambda: self._edit_patient_by_id(pid))
        menu.add_command(label="Delete", command=lambda: self._delete_by_id(pid))
        menu.add_command(label="Copy name", command=lambda: self._copy_name_by_id(pid))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _edit_patient_by_id(self, pid):
        panel = self.patient_panels.get(pid)
        if panel is not None and panel.winfo_exists():
            panel._edit_patient_info()

    def _delete_by_id(self, pid):
        try:
            if messagebox.askyesno(lang.t("app_name"), "Delete this patient and all their data?"):
                page = self.patient_panels.pop(pid, None)
                if page is not None:
                    try:
                        if page.winfo_exists():
                            page.destroy()
                    except Exception:
                        pass
                db.delete_patient(pid)
                if self.selected_patient_id == pid:
                    self.selected_patient_id = None
                    self._show_placeholder()
                self.refresh_patients_db()
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _copy_name_by_id(self, pid):
        p = db.get_patient(patient_id=pid)
        if p:
            self.clipboard_clear()
            self.clipboard_append(p.get('name', ''))

    def _open_patient_by_id(self, patient_id):
        self.selected_patient_id = patient_id
        for w in self.file_host.winfo_children():
            w.destroy()
        panel = PatientFilePanel(self.file_host, patient_id, on_close=self.refresh_patients_db)
        panel.grid(row=0, column=0, sticky="nsew")
        self.patient_panels[patient_id] = panel
        self.refresh_patients_db()


    def _open_patient_file(self):
        if self.selected_patient_id is None:
            messagebox.showinfo(lang.t("app_name"), lang.t("msg_select_patient"))
            return
        self._open_patient_by_id(self.selected_patient_id)

    def _delete_patient_db(self):
        if self.selected_patient_id is None:
            messagebox.showinfo(lang.t("app_name"), lang.t("msg_select_patient"))
            return
        self._delete_by_id(self.selected_patient_id)

    def _clear_search(self):
        try:
            self.search_entry.delete(0, "end")
        except Exception:
            pass
        self.refresh_patients_db()

    def _on_language_change(self, choice):
        code = "ro" if choice == "Română" else "en"
        if code == lang.get_language():
            return
        lang.set_language(code)
        save_language(code)
        self._build_header_bar() if False else None
        self.refresh_patients_db()
        self.title(lang.t("app_name"))

    def _clear_search(self):
        try:
            self.search_entry.delete(0, "end")
        except Exception:
            pass
        self.refresh_patients_db()

    def _toggle_theme(self):
        cur = ctk.get_appearance_mode()
        new_mode = "Dark" if cur == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        try:
            data = load_settings()
            data["appearance"] = new_mode
            save_settings(data)
        except Exception:
            pass
        if hasattr(self, "theme_btn"):
            self.theme_btn.configure(text=new_mode)

    def _export_csv(self):
        try:
            import csv
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Export CSV")
            if not path:
                return
            patients = db.get_all_patients()
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                w = csv.writer(fh, delimiter=";")
                w.writerow(["Nr.", "Nume Pacient", "Localitate", "Diagnostic", "Obiectiv", "Evaluare", "Observatii"])
                for i, p in enumerate(patients, 1):
                    w.writerow([i, p.get('name',''), p.get('localitate',''), p.get('diagnostic',''),
                                p.get('objective',''), p.get('evaluation',''), p.get('observation','')])
            messagebox.showinfo(lang.t("app_name"), "Export CSV reusit")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _sort_by(self, col):
        if self.sort_by == col:
            self.sort_dir = "desc" if self.sort_dir == "asc" else "asc"
        else:
            self.sort_by = col
            self.sort_dir = "asc"
        try:
            data = load_settings()
            data["sort_by"] = self.sort_by
            data["sort_dir"] = self.sort_dir
            save_settings(data)
        except Exception:
            pass
        self.refresh_patients_db()

    def _show_context_menu(self, event):
        iid = self.patients_db_tree.identify_row(event.y)
        if iid:
            self.patients_db_tree.selection_set(iid)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Open", command=self._open_patient_file)
        menu.add_command(label="Edit patient", command=self._edit_selected_patient)
        menu.add_command(label="Copy name", command=self._copy_selected_name)
        menu.add_separator()
        menu.add_command(label="Delete", command=self._delete_patient_db)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _edit_selected_patient(self):
        sel = self.patients_db_tree.selection()
        if not sel:
            return
        patient_id = int(sel[0])
        page = self.patient_pages.get(patient_id)
        if page is not None and page.winfo_exists():
            # open edit dialog via the page
            page._edit_patient_info()
            return
        # fallback: open file then edit
        self._open_patient_file()
        page = self.patient_pages.get(patient_id)
        if page is not None and page.winfo_exists():
            page._edit_patient_info()

    def _copy_selected_name(self):
        sel = self.patients_db_tree.selection()
        if not sel:
            return
        values = self.patients_db_tree.item(sel[0])['values']
        name = values[1] if len(values) > 1 else ""
        self.clipboard_clear()
        self.clipboard_append(name)

    def _save_as(self):
        dlg = SaveAsDialog(self)
        self.wait_window(dlg)
        if not dlg.result:
            return
        fmt = dlg.result
        try:
            if fmt == "excel":
                self._export_excel()
            elif fmt == "csv":
                self._export_csv()
            elif fmt == "pdf":
                self._export_pdf()
            elif fmt == "word":
                self._export_word()
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _export_excel(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="Save as Excel")
            if not path:
                return
            wb = Workbook()
            ws = wb.active
            ws.title = "Pacienti"
            headers = ["Nr.", "Nume Pacient", "Localitate", "Diagnostic", "Obiectiv", "Evaluare", "Observatii"]
            ws.append(headers)
            for c in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=c)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="4472C4")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            patients = db.get_all_patients()
            for i, p in enumerate(patients, 1):
                ws.append([i, p.get('name',''), p.get('localitate',''), p.get('diagnostic',''),
                           p.get('objective',''), p.get('evaluation',''), p.get('observation','')])
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
            widths = [6, 26, 16, 40, 40, 40, 40]
            for idx, w in enumerate(widths, start=1):
                ws.column_dimensions[chr(64 + idx)].width = w
            ws.freeze_panes = "A2"
            wb.save(path)
            messagebox.showinfo(lang.t("app_name"), "Export Excel reusit")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _export_pdf(self):
        try:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], title="Save as PDF")
            if not path:
                return
            patients = db.get_all_patients()
            lines = []
            lines.append("Patient Database")
            lines.append("=" * 60)
            for p in patients:
                lines.append("")
                lines.append("Name: " + str(p.get('name','')))
                lines.append("Locality: " + str(p.get('localitate','')))
                for fld in ("diagnostic", "objective", "evaluation", "observation"):
                    val = (p.get(fld, '') or '').replace("\n", " | ")
                    lines.append(fld.capitalize() + ": " + val)
                lines.append("-" * 60)
            text = "\n".join(lines)
            pdf = _make_simple_pdf(text)
            with open(path, "wb") as fh:
                fh.write(pdf)
            messagebox.showinfo(lang.t("app_name"), "Export PDF reusit")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _export_word(self):
        try:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".doc", filetypes=[("Word", "*.doc")], title="Save as Word")
            if not path:
                return
            patients = db.get_all_patients()
            parts = []
            parts.append(r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}")
            parts.append(r"\title Patient Database")
            for p in patients:
                parts.append(r"\par \b " + _rtf_escape(p.get('name','')) + r"\b0")
                parts.append(r"\par Locality: " + _rtf_escape(p.get('localitate','')))
                for fld in ("diagnostic", "objective", "evaluation", "observation"):
                    val = (p.get(fld, '') or '').replace("\n", "\\par ")
                    parts.append(r"\par \b " + fld.capitalize() + r":\b0 " + _rtf_escape(val))
                parts.append(r"\par " + "-" * 40)
            parts.append("}")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("".join(parts))
            messagebox.showinfo(lang.t("app_name"), "Export Word reusit")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _export_access(self):
        self._export_csv()

    def _backup_now(self):
        try:
            import shutil, datetime
            folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")
            os.makedirs(folder, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(folder, "patients_" + stamp + ".db")
            shutil.copy2(db.db_path(), dest)
            files = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".db")])
            while len(files) > 7:
                try:
                    os.remove(files.pop(0))
                except OSError:
                    break
            messagebox.showinfo(lang.t("app_name"), "Backup created:\n" + dest)
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _restore_backup(self):
        try:
            folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")
            if not os.path.isdir(folder):
                messagebox.showinfo(lang.t("app_name"), "No backups found.")
                return
            files = sorted([f for f in os.listdir(folder) if f.endswith(".db")], reverse=True)
            if not files:
                messagebox.showinfo(lang.t("app_name"), "No backups found.")
                return
            dlg = RestoreBackupDialog(self, folder, files)
            self.wait_window(dlg)
            if dlg.result:
                import shutil
                shutil.copy2(os.path.join(folder, dlg.result), db.db_path())
                self.refresh_patients_db()
                messagebox.showinfo(lang.t("app_name"), "Restore complete.")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _import_data(self):
        try:
            from tkinter import filedialog
            path = filedialog.askopenfilename(title="Import (CSV/Excel)", filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx"), ("All", "*.*")])
            if not path:
                return
            import csv
            rows = []
            if path.lower().endswith(".csv"):
                with open(path, newline="", encoding="utf-8-sig") as fh:
                    reader = csv.reader(fh, delimiter=";")
                    next(reader, None)
                    for r in reader:
                        rows.append(r)
            else:
                from openpyxl import load_workbook
                wb = load_workbook(path)
                ws = wb.active
                for r in ws.iter_rows(min_row=2, values_only=True):
                    rows.append(list(r))
            count = 0
            for r in rows:
                if not r or not r[0]:
                    continue
                name = str(r[0]).strip()
                if not name:
                    continue
                loc = str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""
                diag = str(r[2]).strip() if len(r) > 2 and r[2] is not None else ""
                obj = str(r[3]).strip() if len(r) > 3 and r[3] is not None else ""
                eva = str(r[4]).strip() if len(r) > 4 and r[4] is not None else ""
                obs = str(r[5]).strip() if len(r) > 5 and r[5] is not None else ""
                try:
                    pid = db.ensure_patient_exists(name)
                    if pid is not None:
                        db.update_patient(pid, localitate=loc, diagnostic=diag, objective=obj, evaluation=eva, observation=obs)
                        count += 1
                except Exception:
                    pass
            self.refresh_patients_db()
            messagebox.showinfo(lang.t("app_name"), "Imported " + str(count) + " patients.")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _show_trash(self):
        dlg = TrashDialog(self)
        self.wait_window(dlg)
        self.refresh_patients_db()

    def _auto_backup(self):
        try:
            import shutil, datetime
            folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")
            os.makedirs(folder, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d")
            dest = os.path.join(folder, "patients_auto_" + stamp + ".db")
            if not os.path.exists(dest):
                shutil.copy2(db.db_path(), dest)
            files = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".db")])
            while len(files) > 7:
                try:
                    os.remove(files.pop(0))
                except OSError:
                    break
        except Exception:
            pass

    def _keyboard_shortcuts(self, event):
        pass

    def _add_patient_db(self):
        dlg = AddPatientDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            try:
                existing = db.get_patient(name=dlg.result['name'])
                if existing:
                    if messagebox.askyesno(lang.t("app_name"), "Patient already exists. Open their file?"):
                        pid = existing['id']
                        self._open_patient_by_id(pid)
                        return
                    else:
                        return
                pid = db.add_patient(dlg.result['name'], dlg.result['localitate'], sex=dlg.result.get('sex',''), dob=dlg.result.get('dob',''))
                db.update_patient(pid,
                    diagnostic=dlg.result['diagnostic'],
                    objective=dlg.result['objective'],
                    evaluation=dlg.result['evaluation'],
                    observation=dlg.result['observation'],
                    sex=dlg.result.get('sex',''),
                    dob=dlg.result.get('dob',''))
                self.refresh_patients_db()
                self.known_patients = db.get_patient_names()
            except Exception as e:
                messagebox.showerror(lang.t("app_name"), str(e))
    

    def _delete_patient_db(self):
        sel = self.patients_db_tree.selection()
        if not sel:
            messagebox.showinfo(lang.t("app_name"), lang.t("msg_select_patient"))
            return
        patient_id = int(sel[0])
        values = self.patients_db_tree.item(sel[0])['values']
        name = values[1]
        if messagebox.askyesno(lang.t("app_name"), lang.t("confirm_delete_patient", name=name)):
            try:
                # Close any open patient file window for this patient
                page = self.patient_pages.pop(patient_id, None)
                if page is not None:
                    try:
                        if page.winfo_exists():
                            page.destroy()
                    except Exception:
                        pass
                db.delete_patient(patient_id)
                self.refresh_patients_db()
                self.known_patients = db.get_patient_names()
            except Exception as e:
                messagebox.showerror(lang.t("app_name"), str(e))
    
    def _export_excel(self):
        try:
            from openpyxl import Workbook
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="Export Excel")
            if not path:
                return
            wb = Workbook()
            ws = wb.active
            ws.title = "Pacienti"
            ws.append(["Nr.", "Nume Pacient", "Localitate", "Diagnostic", "Observatii"])
            patients = db.get_all_patients()
            for i, p in enumerate(patients, 1):
                ws.append([i, p['name'], p.get('localitate',''), p.get('diagnostic',''), p.get('observation','')])
            wb.save(path)
            messagebox.showinfo(lang.t("app_name"), "Export Excel reusit")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))
    
    def _export_access(self):
        try:
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".mdb", filetypes=[("Access", "*.mdb;*.accdb")], title="Export Access")
            if not path:
                return
            messagebox.showinfo(lang.t("app_name"), "Pentru export Access instaleaza pyodbc si MS Access Driver")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))


class AddPatientDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title(lang.t("dlg_add_patient"))
        self.geometry("460x560")
        self.minsize(420, 480)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.result = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(scroll, text=lang.t("label_patient_name") + ":").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.entry_name = ctk.CTkEntry(scroll)
        self.entry_name.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(scroll, text=lang.t("label_localitate") + ":").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.entry_loc = ctk.CTkComboBox(scroll, values=db.get_localities())
        self.entry_loc.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(scroll, text="Sex:").grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.entry_sex = ctk.CTkComboBox(scroll, values=["NA", "M", "F"])
        self.entry_sex.set("NA")
        self.entry_sex.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(scroll, text="Date of birth (DD.MM.YYYY):").grid(row=6, column=0, sticky="w", pady=(0, 2))
        self.entry_dob = ctk.CTkEntry(scroll)
        self.entry_dob.grid(row=7, column=0, sticky="ew", pady=(0, 8))

        fields = [("diagnostic", lang.t("label_diagnostic")),
                  ("objective", lang.t("label_objective")),
                  ("evaluation", lang.t("label_evaluation")),
                  ("observation", lang.t("label_observation"))]
        self.texts = {}
        r = 8
        for field, lbl in fields:
            ctk.CTkLabel(scroll, text=lbl + ":").grid(row=r, column=0, sticky="w", pady=(0, 2))
            r += 1
            txt = ctk.CTkTextbox(scroll, height=90)
            txt.grid(row=r, column=0, sticky="ew", pady=(0, 8))
            self.texts[field] = txt
            r += 1

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="e", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text=lang.t("btn_ok"), width=80, command=self._ok).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text=lang.t("btn_cancel"), width=80, command=self.destroy).pack(side="left", padx=2)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.entry_name.focus()

    def _ok(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showerror(lang.t("app_name"), lang.t("err_patient_name_required"))
            return
        sex = self.entry_sex.get().strip()
        if sex == "NA":
            sex = ""
        self.result = {
            "name": name,
            "localitate": self.entry_loc.get().strip(),
            "sex": sex,
            "dob": self.entry_dob.get().strip(),
            "diagnostic": self.texts["diagnostic"].get("1.0", "end-1c").strip(),
            "objective": self.texts["objective"].get("1.0", "end-1c").strip(),
            "evaluation": self.texts["evaluation"].get("1.0", "end-1c").strip(),
            "observation": self.texts["observation"].get("1.0", "end-1c").strip(),
        }
        self.destroy()




def _rtf_escape(text):
    text = str(text)
    text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return text


def _make_simple_pdf(text):
    lines = text.split("\n")
    def esc(t):
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content_lines = ["BT", "/F1 10 Tf", "50 780 Td", "12 TL"]
    for ln in lines:
        content_lines.append("(" + esc(ln[:110]) + ") Tj T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")
    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n")
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(b"5 0 obj\n<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream\nendobj\n")
    out = b"%PDF-1.4\n"
    offsets = []
    for o in objects:
        offsets.append(len(out))
        out += o
    xref_pos = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    return out


class SaveAsDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Save as")
        self.geometry("300x260")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result = None
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Choose format:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.fmt = tk.StringVar(value="excel")
        for i, (val, lbl) in enumerate([("excel", "Excel (.xlsx)"), ("csv", "CSV / Access"), ("pdf", "PDF"), ("word", "Word (.doc)")]):
            ctk.CTkRadioButton(self, text=lbl, variable=self.fmt, value=val).grid(row=i+1, column=0, padx=20, pady=4, sticky="w")
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=6, column=0, sticky="e", padx=10, pady=10)
        ctk.CTkButton(btns, text="OK", width=80, command=self._ok).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Cancel", width=80, command=self.destroy).pack(side="left", padx=2)

    def _ok(self):
        self.result = self.fmt.get()
        self.destroy()


class RestoreBackupDialog(ctk.CTkToplevel):
    def __init__(self, master, folder, files):
        super().__init__(master)
        self.title("Restore backup")
        self.geometry("420x320")
        self.transient(master)
        self.grab_set()
        self.result = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        lb = tk.Listbox(self)
        lb.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        for f in files:
            lb.insert("end", f)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="e", padx=10, pady=10)
        def _ok():
            sel = lb.curselection()
            if not sel:
                return
            self.result = lb.get(sel[0])
            self.destroy()
        ctk.CTkButton(btns, text="Restore", width=80, command=_ok).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Cancel", width=80, command=self.destroy).pack(side="left", padx=2)


class TrashDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Deleted patients (trash)")
        self.geometry("520x360")
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        cols = ("name", "localitate", "deleted_at")
        tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        tree.heading("name", text="Name")
        tree.heading("localitate", text="Locality")
        tree.heading("deleted_at", text="Deleted at")
        tree.column("name", width=200)
        tree.column("localitate", width=120)
        tree.column("deleted_at", width=160)
        tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        rows = db.list_deleted()
        for r in rows:
            tree.insert("", "end", iid=str(r["id"]), values=(r.get("name",""), r.get("localitate",""), r.get("deleted_at","")))
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="e", padx=10, pady=10)
        def _restore():
            sel = tree.selection()
            if not sel:
                return
            try:
                db.restore_deleted(int(sel[0]))
                tree.delete(sel[0])
            except Exception as e:
                messagebox.showerror(lang.t("app_name"), str(e))
        def _purge():
            sel = tree.selection()
            if not sel:
                return
            if not messagebox.askyesno(lang.t("app_name"), "Permanently delete?"):
                return
            conn = db._get_conn()
            conn.execute("DELETE FROM deleted_patients WHERE id = ?", (int(sel[0]),))
            conn.commit()
            conn.close()
            tree.delete(sel[0])
        ctk.CTkButton(btns, text="Restore", width=80, command=_restore).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Purge", width=80, fg_color="#c0392b", command=_purge).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Close", width=80, command=self.destroy).pack(side="left", padx=2)



class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Settings")
        self.geometry("420x460")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Settings", font=theme.FONT_TITLE, text_color=theme.TEXT).grid(
            row=0, column=0, sticky="w", padx=theme.PADDING, pady=(theme.PADDING, 8))

        # Language
        ctk.CTkLabel(self, text="Language:", font=theme.FONT_BOLD, text_color=theme.TEXT).grid(
            row=1, column=0, sticky="w", padx=theme.PADDING, pady=(4, 2))
        self.lang_menu = ctk.CTkOptionMenu(self, values=list(LANG_LABELS.values()), width=200,
                                          command=master._on_language_change)
        self.lang_menu.set(LANG_LABELS.get(lang.get_language(), "English"))
        self.lang_menu.grid(row=2, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))

        # Theme
        ctk.CTkLabel(self, text="Theme:", font=theme.FONT_BOLD, text_color=theme.TEXT).grid(
            row=3, column=0, sticky="w", padx=theme.PADDING, pady=(4, 2))
        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.grid(row=4, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))
        ctk.CTkButton(theme_frame, text="Light", width=90, command=lambda: (ctk.set_appearance_mode("Light"), master._toggle_theme() if False else None)).pack(side="left", padx=2)
        ctk.CTkButton(theme_frame, text="Dark", width=90, command=lambda: ctk.set_appearance_mode("Dark")).pack(side="left", padx=2)

        # Backup / Restore / Import
        ctk.CTkLabel(self, text="Data:", font=theme.FONT_BOLD, text_color=theme.TEXT).grid(
            row=5, column=0, sticky="w", padx=theme.PADDING, pady=(8, 2))
        data_frame = ctk.CTkFrame(self, fg_color="transparent")
        data_frame.grid(row=6, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))
        ctk.CTkButton(data_frame, text="Backup now", width=110, command=master._backup_now).pack(side="left", padx=2)
        ctk.CTkButton(data_frame, text="Restore...", width=110, command=master._restore_backup).pack(side="left", padx=2)
        ctk.CTkButton(data_frame, text="Import...", width=110, command=master._import_data).pack(side="left", padx=2)

        # Trash
        ctk.CTkButton(self, text="Open Trash (deleted patients)", width=220, command=master._show_trash).grid(
            row=7, column=0, sticky="w", padx=theme.PADDING, pady=(8, 8))

        ctk.CTkButton(self, text="Close", width=90, command=self.destroy).grid(
            row=8, column=0, sticky="e", padx=theme.PADDING, pady=(8, theme.PADDING))


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
