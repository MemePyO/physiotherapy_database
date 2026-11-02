"""Frontend: customtkinter GUI with Patient Database."""
import json
import os
import sys
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

import lang
import db
import theme
import log
from version import __version__
logger = log.get_logger(__name__)


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _asset_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return _base_dir()
from patient_panel import PatientFilePanel
from utils import _norm, _initials, _validate_dob, _rtf_escape, _make_simple_pdf, _strip_inline_formatting
import utils
from tooltip import attach_tooltip, hide_tooltip
from dialogs import (AddPatientDialog, SaveAsDialog, RestoreBackupDialog,
                     TrashDialog, SettingsDialog, ExportFieldsDialog)

APP_NAME = "Patient Database"

EXPORT_FIELDS = [
    ("nr", "Nr."),
    ("name", "Nume Pacient"),
    ("localitate", "Localitate"),
    ("sex", "Sex"),
    ("dob", "DOB"),
    ("patient_code", "Cod pacient"),
    ("diagnostic", "Diagnostic"),
    ("objective", "Obiectiv"),
    ("evaluation", "Evaluare"),
    ("observation", "Observatii"),
    ("created_at", "Creat"),
    ("updated_at", "Modificat"),
]


def _field_value(p, key, idx):
    if key == "nr":
        return idx
    if key == "name":
        return p.get("name", "")
    if key == "localitate":
        return p.get("localitate", "")
    if key == "sex":
        return p.get("sex", "")
    if key == "dob":
        return p.get("dob", "")
    if key == "patient_code":
        return p.get("patient_code", "")
    if key == "diagnostic":
        return p.get("diagnostic", "")
    if key == "objective":
        return p.get("objective", "")
    if key == "evaluation":
        return p.get("evaluation", "")
    if key == "observation":
        return p.get("observation", "")
    if key == "created_at":
        return p.get("created_at", "")
    if key == "updated_at":
        return p.get("updated_at", "")
    return ""

LANG_LABELS = {"en": "English", "ro": "Română"}


def settings_file():
    return os.path.join(_base_dir(), "settings.json")


def load_settings():
    try:
        with open(settings_file(), encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return {}
        # validate / sanitize
        if "ui_scale" in data:
            try:
                s = float(data["ui_scale"])
                if s not in (1.0, 1.25, 1.5):
                    data["ui_scale"] = 1.0
            except (TypeError, ValueError):
                data["ui_scale"] = 1.0
        if data.get("ui_theme") not in ("classic", "medidash"):
            data["ui_theme"] = "classic"
        if data.get("appearance") not in ("Light", "Dark"):
            data["appearance"] = "Light"
        if data.get("sort_by") not in ("name", "localitate", "diagnostic", "updated", "created", "nr"):
            data["sort_by"] = "name"
        if data.get("sort_dir") not in ("asc", "desc"):
            data["sort_dir"] = "asc"
        return data
    except (OSError, ValueError):
        return {}


def save_settings(data):
    try:
        path = settings_file()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass


def load_language():
    code = str(load_settings().get("language", "en"))
    return code if code in lang.LANGS else "en"


def save_language(code):
    data = load_settings()
    data["language"] = code
    save_settings(data)



class App(ctk.CTk):
    """Main application window: sidebar navigation, patient overview, and embedded patient file."""

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
            scale = settings.get("ui_scale", 1.0)
            try:
                ctk.set_widget_scaling(scale)
                ctk.set_window_scaling(scale)
            except Exception as e:
                log.debug_exc(logger)
            theme._appearance = mode
            ctk.set_appearance_mode(mode)
            theme.set_theme(settings.get("ui_theme", "classic"))
        except Exception:
            self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        # Initialize database
        db.init_db()
        try:
            if not db.check_integrity():
                if messagebox.askyesno(lang.t("app_name"), "Database integrity check failed. Restore from latest backup?"):
                    # find latest backup by modification time (not name)
                    import glob as _g
                    folder = os.path.join(_base_dir(), "backup")
                    files = _g.glob(os.path.join(folder, "*.db"))
                    files = [f for f in files if os.path.basename(f).startswith(("auto_", "pre_migration_", "pre_purge_"))]
                    if files:
                        latest = max(files, key=os.path.getmtime)
                        try:
                            import shutil
                            shutil.copy2(latest, db.db_path())
                            # ensure schema tables exist even if the backup predates a migration
                            db.init_db()
                            messagebox.showinfo(lang.t("app_name"), "Restored from " + os.path.basename(latest))
                        except Exception as e:
                            messagebox.showerror(lang.t("app_name"), str(e))
        except Exception as e:
            log.debug_exc(logger)
        self.patients_file = patients_file
        self.list_error = None
        try:
            self.known_patients = db.get_patient_names()
        except Exception as exc:
            self.known_patients = []
            self.list_error = str(exc)

        _st = load_settings()
        self.sort_by = _st.get("sort_by", "name")
        self.sort_dir = _st.get("sort_dir", "asc")
        self.search_scope = "everything"
        self.selected_patient_id = None
        self._current_panel = None
        self._last_deleted_row_id = None
        self._last_deleted_name = None
        self.patient_panels = {}
        self._card_widgets = {}
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
        self._sidebar_visible = True
        self.bind("<Configure>", self._on_configure_responsive)
        # never leave a tooltip behind when the window is hidden or the user clicks
        self.bind("<Unmap>", lambda e: hide_tooltip(), add="+")
        self.bind_all("<Button-1>", lambda e: hide_tooltip(), add="+")
        # Keyboard shortcuts
        self.bind("<Control-n>", lambda e: self._open_patient_by_id(None))
        self.bind("<Control-f>", lambda e: (self._focus_search(), "break")[1])
        self.bind("<Control-z>", self._handle_ctrl_z)
        self.bind("<Control-y>", self._handle_ctrl_y)
        self.bind("<Control-Z>", self._handle_ctrl_z)
        self.bind("<Control-Y>", self._handle_ctrl_y)
        self.bind("<Control-s>", self._save_current_panel)
        self.bind("<Control-p>", self._print_current_panel)
        self.bind("<Escape>", self._handle_escape)

    def _on_app_close(self):
        try:
            self._save_open_files()
        except Exception as e:
            log.debug_exc(logger)
        try:
            data = load_settings()
            data["geometry"] = self.geometry()
            save_settings(data)
        except Exception as e:
            log.debug_exc(logger)
        self.destroy()

    def _save_current_panel(self):
        panel = getattr(self, "patient_panels", {}).get(self.selected_patient_id)
        if panel is None or not panel.winfo_exists():
            return "break"
        panel._save_all(silent=True)
        return "break"

    def _print_current_panel(self):
        panel = getattr(self, "patient_panels", {}).get(self.selected_patient_id)
        if panel is not None and panel.winfo_exists():
            panel._print_pdf()
        return "break"

    def _focus_search(self):
        entry = getattr(self, "search_entry", None)
        if entry is not None:
            try:
                if entry.winfo_exists():
                    entry.focus_set()
                    return
            except Exception as e:
                log.debug_exc(logger)
        # medidash theme has no inline search box
        try:
            self._search_patients_dialog()
        except Exception as e:
            log.debug_exc(logger)
    def _handle_escape(self, event=None):
        try:
            entry = getattr(self, "search_entry", None)
            if entry is not None and entry.winfo_exists() and self.focus_get() is entry:
                if entry.get():
                    self._clear_search()
                    return "break"
            self._focus_search()
        except Exception as e:
            log.debug_exc(logger)
        return "break"

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
        help_menu.add_command(label="Keyboard shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="About", command=lambda: messagebox.showinfo(lang.t("app_name"), "Patient Database\nVersion " + __version__ + "\nSQLite-backed patient records."))
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _show_shortcuts(self):
        text = (
            "Ctrl+N   New patient\n"
            "Ctrl+F   Focus search\n"
            "Ctrl+S   Save current patient file\n"
            "Ctrl+P   Print / PDF current patient\n"
            "Ctrl+Z   Undo last delete\n"
            "\n"
            "\u2191 / \u2193    Previous / next patient\n"
            "Enter    Open selected patient\n"
            "Esc      Back to search"
        )
        messagebox.showinfo("Keyboard shortcuts", text)

    def _on_language_change(self, choice):
        code = "ro" if choice == "Română" else "en"
        if code == lang.get_language():
            return
        lang.set_language(code)
        save_language(code)
        self.refresh_patients_db()
        self.title(lang.t("app_name"))

    def _build_header_bar(self):
        if theme.active().startswith("medidash"):
            self._build_header_bar_medidash()
            return
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=theme.PADDING, pady=(10, 6))
        bar.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(brand, text="Medi", font=theme.FONT_TITLE, text_color=theme.TEXT).pack(side="left")
        ctk.CTkLabel(brand, text="Dashboard Pro", font=theme.FONT_TITLE, text_color=theme.ACCENT).pack(side="left")

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(right, text="\u2630", width=40, font=theme.ICON_FONT_SMALL, command=self._toggle_sidebar).pack(side="left", padx=2)
        ctk.CTkButton(right, text="Theme", width=70, command=self._toggle_theme).pack(side="left", padx=2)
        self.lang_menu = ctk.CTkOptionMenu(right, values=list(LANG_LABELS.values()), width=95, command=self._on_language_change)
        self.lang_menu.set(LANG_LABELS.get(lang.get_language(), "English"))
        self.lang_menu.pack(side="left", padx=2)

    def _build_header_bar_medidash(self):
        bar = ctk.CTkFrame(self, fg_color=theme.TOPBAR_BG, height=theme.TOPBAR_H, corner_radius=0,
                            border_width=1, border_color=theme.BORDER)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)
        self._header = bar

        # brand
        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w", padx=20)
        try:
            img = ctk.CTkImage(light_image=__import__("PIL.Image", fromlist=["Image"]).open(
                os.path.join(_asset_dir(), "assets", "logo.png")), size=(40, 40))
            ctk.CTkLabel(brand, image=img, text="").pack(side="left", padx=(0, 10))
        except Exception:
            ctk.CTkLabel(brand, text="\u2695", font=("Segoe UI", 26), text_color=theme.ACCENT).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(brand, text="MediDashboard", font=theme.FONT_TITLE, text_color=theme.TEXT).pack(side="left")
        ctk.CTkLabel(brand, text="Pro", font=theme.FONT_TITLE, text_color=theme.ACCENT).pack(side="left", padx=(4, 0))

        # right actions
        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e", padx=20)
        ctk.CTkButton(right, text="\uE700", width=36, height=36, font=theme.ICON_FONT_SMALL,
                      fg_color="transparent", text_color=theme.MUTED, hover_color=theme.ACCENT_LIGHT,
                      command=self._toggle_sidebar).pack(side="left", padx=2)
        ctk.CTkButton(right, text="\uE721", width=36, height=36, font=theme.ICON_FONT_SMALL,
                      fg_color="transparent", text_color=theme.MUTED, hover_color=theme.ACCENT_LIGHT,
                      command=self._search_patients_dialog).pack(side="left", padx=2)
        ctk.CTkButton(right, text="\uE70F", width=36, height=36, font=theme.ICON_FONT_SMALL,
                      fg_color="transparent", text_color=theme.MUTED, hover_color=theme.ACCENT_LIGHT,
                      command=self._edit_current_patient).pack(side="left", padx=2)
        self.lang_menu = ctk.CTkOptionMenu(right, values=list(LANG_LABELS.values()), width=90,
                                            command=self._on_language_change)
        self.lang_menu.set(LANG_LABELS.get(lang.get_language(), "English"))
        self.lang_menu.pack(side="left", padx=6)
        account = ctk.CTkButton(right, text="\uE77B \uE70D", width=60, height=36, font=theme.ICON_FONT_SMALL,
                                fg_color="transparent", text_color=theme.MUTED, hover_color=theme.ACCENT_LIGHT,
                                command=self._show_account_menu)
        account.pack(side="left", padx=2)
        self._account_btn = account

    def _build_sidebar(self):
        if theme.active().startswith("medidash"):
            self._build_sidebar_medidash()
            return
        side = ctk.CTkFrame(self, width=theme.SIDEBAR_W, fg_color=theme.SIDEBAR_BG, corner_radius=0)
        side.grid(row=1, column=0, sticky="nsw", padx=(8, 0), pady=8)
        side.grid_propagate(False)
        self._sidebar = side

        logo = ctk.CTkLabel(side, text="\u2695", font=("Segoe UI", 26), text_color=theme.ACCENT)
        logo.pack(pady=(12, 18))

        self._nav_buttons = {}
        items = [("patients", "\U0001F4CB", "Patients", lambda: self._show_view("patients"), theme.ICON_FONT),
                 ("new", "\u2795", "New", lambda: self._open_patient_by_id(None), theme.ICON_FONT),
                 ("saveas", "\U0001F4BE", "Save as", lambda: self._show_view("saveas"), theme.ICON_FONT),
                 ("backup", "\U0001F5C4", "Backup", lambda: self._show_view("backup"), theme.ICON_FONT),
                 ("trash", "\U0001F5D1", "Trash", lambda: self._show_view("trash"), theme.ICON_FONT),
                 ("calendar", "\U0001F4C5", "Calendar", lambda: self._show_view("calendar"), theme.ICON_FONT),
                 ("settings", "\u2699", "Settings", lambda: self._show_view("settings"), theme.ICON_FONT)]
        for key, glyph, tip, cmd, font in items:
            btn = ctk.CTkButton(side, text=glyph, width=44, height=44, corner_radius=12,
                                fg_color="transparent", text_color=theme.TEXT, hover_color=theme.SIDEBAR_ACTIVE,
                                font=font, command=cmd, border_width=2,
                                border_color=theme.BORDER)
            btn.pack(pady=4)
            self._nav_buttons[key] = btn
            attach_tooltip(btn, tip)
        self._set_nav_active("patients")

    def _build_sidebar_medidash(self):
        side = ctk.CTkFrame(self, width=theme.RAIL_W, fg_color=theme.RAIL_BG, corner_radius=0,
                            border_width=0)
        side.grid(row=1, column=0, sticky="nsw")
        side.grid_propagate(False)
        self._sidebar = side

        self._nav_buttons = {}
        items = [("patients", "\uE716", "Patients", lambda: self._show_view("patients")),
                 ("new", "\uE710", "New patient", lambda: self._open_patient_by_id(None)),
                 ("saveas", "\uE8A5", "Save as", lambda: self._show_view("saveas")),
                 ("backup", "\uE753", "Backup", lambda: self._show_view("backup")),
                 ("trash", "\uE74D", "Trash", lambda: self._show_view("trash")),
                 ("calendar", "\uE787", "Calendar", lambda: self._show_view("calendar"))]
        for key, glyph, tip, cmd in items:
            btn = ctk.CTkButton(side, text=glyph, width=40, height=40, corner_radius=theme.BTN_RADIUS,
                                fg_color="transparent", text_color=theme.MUTED, hover_color=theme.ACCENT_LIGHT,
                                font=theme.ICON_FONT, command=cmd)
            btn.pack(pady=6, padx=12)
            self._nav_buttons[key] = btn
            attach_tooltip(btn, tip)
        # settings pinned to bottom
        btn = ctk.CTkButton(side, text="\uE713", width=40, height=40, corner_radius=theme.BTN_RADIUS,
                            fg_color="transparent", text_color=theme.MUTED, hover_color=theme.ACCENT_LIGHT,
                            font=theme.ICON_FONT, command=lambda: self._show_view("settings"))
        btn.pack(side="bottom", pady=16, padx=12)
        self._nav_buttons["settings"] = btn
        attach_tooltip(btn, "Settings")
        self._set_nav_active("patients")

    def _set_nav_active(self, key):
        if theme.active().startswith("medidash"):
            for k, b in getattr(self, "_nav_buttons", {}).items():
                if k == key:
                    b.configure(fg_color=theme.ACCENT, text_color="#ffffff")
                else:
                    b.configure(fg_color="transparent", text_color=theme.MUTED)
            return
        for k, b in getattr(self, "_nav_buttons", {}).items():
            b.configure(fg_color=theme.SIDEBAR_ACTIVE if k == key else "transparent")

    def _toggle_sidebar(self):
        if getattr(self, "_sidebar_visible", True):
            try:
                self._sidebar.grid_remove()
            except Exception as e:
                log.debug_exc(logger)
            self._sidebar_visible = False
        else:
            try:
                self._sidebar.grid()
            except Exception as e:
                log.debug_exc(logger)
            self._sidebar_visible = True

    def _on_configure_responsive(self, event=None):
        try:
            if self.winfo_width() < 900 and getattr(self, "_sidebar_visible", True):
                self._sidebar.grid_remove()
                self._sidebar_visible = False
            elif self.winfo_width() >= 950 and not getattr(self, "_sidebar_visible", False):
                self._sidebar.grid()
                self._sidebar_visible = True
        except Exception as e:
            log.debug_exc(logger)
    def _nav_patients(self):
        self._set_nav_active("patients")

    def _nav_settings(self):
        self._set_nav_active("settings")
        dlg = SettingsDialog(self)
        self.wait_window(dlg)

    def _build_content(self):
        if theme.active().startswith("medidash"):
            self._build_content_medidash()
            return
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

    def _build_content_medidash(self):
        content = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=0)
        content.grid(row=1, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=0)
        content.grid_columnconfigure(1, weight=0)
        content.grid_columnconfigure(2, weight=1)
        content.grid_rowconfigure(0, weight=1)
        self._content = content

        self.overview_panel = ctk.CTkFrame(content, fg_color=theme.PANEL, corner_radius=0)
        self.overview_panel.grid(row=0, column=0, sticky="ns")
        self.overview_panel.grid_propagate(False)
        self.overview_panel.configure(width=theme.LIST_W)
        self._build_overview_medidash(self.overview_panel)

        divider = ctk.CTkFrame(content, width=1, fg_color=theme.BORDER, corner_radius=0)
        divider.grid(row=0, column=1, sticky="ns")

        self.file_host = ctk.CTkFrame(content, fg_color=theme.PANEL, corner_radius=0)
        self.file_host.grid(row=0, column=2, sticky="nsew")
        self.file_host.grid_columnconfigure(0, weight=1)
        self.file_host.grid_rowconfigure(0, weight=1)
        self._show_placeholder()



    def _build_overview(self, parent):
        if theme.active().startswith("medidash"):
            self._build_overview_medidash(parent)
            return
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        self.overview_title = ctk.CTkLabel(parent, text=lang.t("ui_patient_overview"), font=theme.FONT_TITLE, text_color=theme.TEXT)
        self.overview_title.grid(row=0, column=0, sticky="w", padx=theme.PADDING, pady=(theme.PADDING, 2))

        self.overview_content = ctk.CTkFrame(parent, fg_color="transparent")
        self.overview_content.grid(row=1, column=0, sticky="nsew", padx=theme.PADDING, pady=(0, theme.PADDING))
        self.overview_content.grid_columnconfigure(0, weight=1)
        self.overview_content.grid_rowconfigure(0, weight=0)

        self._show_view("patients")

    def _build_overview_medidash(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        parent.configure(fg_color=theme.PANEL)

        self.overview_title = ctk.CTkLabel(parent, text=lang.t("ui_patient_overview"), font=theme.FONT_TITLE, text_color=theme.TEXT)
        self.overview_title.grid(row=0, column=0, sticky="w", padx=theme.PANE_PAD, pady=(theme.PANE_PAD, 2))

        self.overview_content = ctk.CTkFrame(parent, fg_color="transparent")
        self.overview_content.grid(row=1, column=0, sticky="nsew", padx=theme.PANE_PAD, pady=(0, theme.PANE_PAD))
        self.overview_content.grid_columnconfigure(0, weight=1)
        self.overview_content.grid_rowconfigure(0, weight=0)

        self._show_view("patients")


    def _show_view(self, view):
        job = getattr(self, "_search_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception as e:
                log.debug_exc(logger)
            self._search_job = None
        try:
            if hasattr(self, "search_entry") and self.search_entry.winfo_exists():
                self._search_text = self.search_entry.get()
            if isinstance(getattr(self, "search_scope", None), str):
                self._search_scope_text = self.search_scope
        except Exception as e:
            log.debug_exc(logger)
        for w in self.overview_content.winfo_children():
            w.destroy()
        # reset any row/column weights left over from the previous view
        for i in range(6):
            try:
                self.overview_content.grid_rowconfigure(i, weight=0)
                self.overview_content.grid_columnconfigure(i, weight=0 if i else 1)
            except Exception as e:
                log.debug_exc(logger)
        self._current_view = view
        titles = {"patients": "Patient Overview", "trash": "Trash (deleted)", "settings": "Settings",
                  "saveas": "Save as", "backup": "Backup / Restore", "new": "New patient",
                  "calendar": "Calendar"}
        self.overview_title.configure(text=titles.get(view, view))
        if view == "patients":
            self._view_patients()
        elif view == "trash":
            self._view_trash()
        elif view == "settings":
            self._view_settings()
        elif view == "saveas":
            self._view_saveas()
        elif view == "backup":
            self._view_backup()
        elif view == "new":
            self._view_new_patient()
        elif view == "calendar":
            self._view_calendar()

    def _view_patients(self):
        f = self.overview_content
        medidash = (theme.active().startswith("medidash"))
        if medidash:
            f.grid_rowconfigure(1, weight=1)
            top = ctk.CTkFrame(f, fg_color="transparent")
            top.grid(row=0, column=0, sticky="ew", pady=(0, 2))
            top.grid_columnconfigure(0, weight=1)
            self.count_label = ctk.CTkLabel(top, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
            self.count_label.grid(row=0, column=0, sticky="w")
            self.sort_btn = ctk.CTkButton(top, text="\u21c5", width=30, command=self._show_sort_menu)
            self.sort_btn.grid(row=0, column=1, padx=(6, 2))
            attach_tooltip(self.sort_btn, "Sort patients")
            clear_btn = ctk.CTkButton(top, text="\u00d7", width=26, command=self._clear_search)
            clear_btn.grid(row=0, column=2, padx=(2, 0))
            attach_tooltip(clear_btn, "Clear search")
            self.search_entry = None

            self.card_list = ctk.CTkScrollableFrame(f, fg_color="transparent")
            self.card_list.grid(row=1, column=0, sticky="nsew", pady=(0, 2))
            self.card_list.grid_columnconfigure(0, weight=1)
            utils._patch_scrollable(self.card_list)

            ctk.CTkButton(f, text=lang.t("ui_new_patient"), height=32, fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK,
                          font=theme.FONT_BOLD, command=lambda: self._open_patient_by_id(None)).grid(
                row=2, column=0, sticky="ew", pady=(2, 0))
            self.refresh_patients_db()
            return

        f.grid_rowconfigure(2, weight=1)
        search_frame = ctk.CTkFrame(f, fg_color=theme.INPUT_BG, corner_radius=9,
                                    border_width=1, border_color=theme.BORDER)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        search_frame.grid_columnconfigure(1, weight=1)
        self.search_scope_menu = ctk.CTkOptionMenu(search_frame, values=["Name", "Everything"], width=95,
                                                   command=lambda v: (setattr(self, "search_scope", v.lower()),
                                                                      self.refresh_patients_db()))
        saved_scope = getattr(self, "_search_scope_text", "everything")
        self.search_scope_menu.set("Name" if saved_scope == "name" else "Everything")
        self.search_scope_menu.pack(side="left", padx=(0, 6))
        self.search_scope = saved_scope
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text=lang.t("ui_search_patients"))
        self.search_entry.pack(side="left", fill="x", expand=True)
        if getattr(self, "_search_text", ""):
            self.search_entry.insert(0, self._search_text)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Down>", lambda e: (self._navigate_patient(1), "break")[1])
        self.search_entry.bind("<Up>", lambda e: (self._navigate_patient(-1), "break")[1])
        self.search_entry.bind("<Return>", lambda e: (self._navigate_patient(1, open_first=True), "break")[1])
        self.search_entry.bind("<Escape>", lambda e: (self._clear_search(), "break")[1])
        ctk.CTkButton(search_frame, text="\u00d7", width=26, command=self._clear_search).pack(side="left", padx=2)
        self.sort_btn = ctk.CTkButton(search_frame, text="\u21c5", width=30, command=self._show_sort_menu)
        self.sort_btn.pack(side="left", padx=(2, 0))
        attach_tooltip(self.sort_btn, "Sort patients")

        self.count_label = ctk.CTkLabel(f, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w")
        self.count_label.grid(row=1, column=0, sticky="ew", pady=(0, 2))

        self.card_list = ctk.CTkScrollableFrame(f, fg_color="transparent")
        self.card_list.grid(row=2, column=0, sticky="nsew", pady=(0, 2))
        self.card_list.grid_columnconfigure(0, weight=1)
        utils._patch_scrollable(self.card_list)

        ctk.CTkButton(f, text=lang.t("ui_new_patient"), height=32, fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK,
                      font=theme.FONT_BOLD, command=lambda: self._open_patient_by_id(None)).grid(
            row=3, column=0, sticky="ew", pady=(2, 0))
        self.refresh_patients_db()

    def _on_search_key(self, event=None):
        """Debounce the search so typing does not rebuild the whole list per key."""
        try:
            if getattr(self, "_search_job", None):
                self.after_cancel(self._search_job)
        except Exception as e:
            log.debug_exc(logger)
        try:
            self._search_job = self.after(150, self.refresh_patients_db)
        except Exception:
            self.refresh_patients_db()

    def _navigate_patient(self, delta, open_first=False):
        """Move the current selection up/down in the filtered patient list."""
        ids = list(getattr(self, "_visible_patient_ids", []))
        if not ids:
            return
        if open_first or self.selected_patient_id not in ids:
            target = ids[0]
        else:
            idx = ids.index(self.selected_patient_id) + delta
            target = ids[max(0, min(idx, len(ids) - 1))]
        if open_first or target != self.selected_patient_id:
            self._open_patient_by_id(target)

    def _view_trash(self):
        f = self.overview_content
        f.grid_rowconfigure(0, weight=1)
        cols = ("name", "localitate", "deleted_at")
        tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="browse")
        tree.heading("name", text=lang.t("ui_name"))
        tree.heading("localitate", text=lang.t("ui_locality"))
        tree.heading("deleted_at", text=lang.t("ui_deleted_at"))
        tree.column("name", width=120)
        tree.column("localitate", width=90)
        tree.column("deleted_at", width=130)
        tree.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        rows = db.list_deleted()
        for r in rows:
            tree.insert("", "end", iid=str(r["id"]), values=(r.get("name",""), r.get("localitate",""), r.get("deleted_at","")))
        btns = ctk.CTkFrame(f, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        def _restore():
            sel = tree.selection()
            if not sel: return
            try:
                db.restore_deleted(int(sel[0]))
                tree.delete(sel[0])
                self.refresh_patients_db()
            except Exception as e:
                messagebox.showerror(lang.t("app_name"), str(e))
        def _restore_all():
            for iid in list(tree.get_children()):
                try:
                    db.restore_deleted(int(iid)); tree.delete(iid)
                except Exception as e:
                    messagebox.showerror(lang.t("app_name"), str(e))
            self.refresh_patients_db()
        def _purge():
            sel = tree.selection()
            if not sel or not messagebox.askyesno(lang.t("app_name"), "Permanently delete?"): return
            db.pre_operation_backup("purge")
            conn = db._get_conn()
            conn.execute("DELETE FROM deleted_patients WHERE id = ?", (int(sel[0]),))
            conn.commit(); conn.close()
            tree.delete(sel[0])
        def _empty():
            if not messagebox.askyesno(lang.t("app_name"), "Empty trash?"): return
            db.pre_operation_backup("purge")
            conn = db._get_conn()
            conn.execute("DELETE FROM deleted_patients")
            conn.commit(); conn.close()
            for iid in list(tree.get_children()):
                tree.delete(iid)
        ctk.CTkButton(btns, text=lang.t("ui_restore"), width=80, command=_restore).pack(side="left", padx=2)
        ctk.CTkButton(btns, text=lang.t("ui_restore_all"), width=90, command=_restore_all).pack(side="left", padx=2)
        ctk.CTkButton(btns, text=lang.t("ui_purge"), width=70, fg_color="#c0392b", command=_purge).pack(side="left", padx=2)
        ctk.CTkButton(btns, text=lang.t("ui_empty_trash"), width=70, fg_color="#c0392b", command=_empty).pack(side="left", padx=2)

    def _view_settings(self):
        f = self.overview_content
        f.grid_rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(f, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        utils._patch_scrollable(scroll)
        ctk.CTkLabel(scroll, text=lang.t("ui_language"), font=theme.FONT_BOLD, text_color=theme.TEXT).pack(anchor="w", pady=(0,2))
        lm = ctk.CTkOptionMenu(scroll, values=list(LANG_LABELS.values()), width=200, command=self._on_language_change)
        lm.set(LANG_LABELS.get(lang.get_language(), "English"))
        lm.pack(anchor="w", pady=(0,10))
        ctk.CTkLabel(scroll, text=lang.t("ui_ui_scale"), font=theme.FONT_BOLD, text_color=theme.TEXT).pack(anchor="w", pady=(8,2))
        sf = ctk.CTkFrame(scroll, fg_color="transparent")
        sf.pack(anchor="w", pady=(0,10))
        for pct in (100, 125, 150):
            ctk.CTkButton(sf, text=str(pct) + "%", width=70,
                          command=lambda p=pct: self._set_ui_scale(p / 100.0)).pack(side="left", padx=2)

        ctk.CTkLabel(scroll, text=lang.t("ui_theme_label"), font=theme.FONT_BOLD, text_color=theme.TEXT).pack(anchor="w", pady=(0,2))
        tf = ctk.CTkFrame(scroll, fg_color="transparent")
        tf.pack(anchor="w", pady=(0,10))
        ctk.CTkButton(tf, text="Light", width=90, command=lambda: self._apply_appearance("Light")).pack(side="left", padx=2)
        ctk.CTkButton(tf, text="Dark", width=90, command=lambda: self._apply_appearance("Dark")).pack(side="left", padx=2)
        ctk.CTkLabel(scroll, text=lang.t("ui_interface_theme"), font=theme.FONT_BOLD, text_color=theme.TEXT).pack(anchor="w", pady=(8,2))
        itf = ctk.CTkFrame(scroll, fg_color="transparent")
        itf.pack(anchor="w", pady=(0,10))
        ctk.CTkButton(itf, text="Classic", width=90, command=lambda: self.after(50, lambda: self._apply_ui_theme("classic"))).pack(side="left", padx=2)
        ctk.CTkButton(itf, text="MediDashboard", width=120, command=lambda: self.after(50, lambda: self._apply_ui_theme("medidash"))).pack(side="left", padx=2)
        ctk.CTkLabel(scroll, text=lang.t("ui_data"), font=theme.FONT_BOLD, text_color=theme.TEXT).pack(anchor="w", pady=(8,2))
        df = ctk.CTkFrame(scroll, fg_color="transparent")
        df.pack(anchor="w", pady=(0,10))
        ctk.CTkButton(df, text="Backup now", width=110, command=self._backup_now).pack(side="left", padx=2)
        ctk.CTkButton(df, text="Restore...", width=110, command=self._restore_backup).pack(side="left", padx=2)
        ctk.CTkButton(df, text="Import...", width=110, command=self._import_data).pack(side="left", padx=2)
        ctk.CTkButton(scroll, text=lang.t("ui_open_trash"), width=200, command=lambda: self._show_view("trash")).pack(anchor="w", pady=(8, 0))

    def _view_saveas(self):
        f = self.overview_content
        f.grid_rowconfigure(0, weight=1)
        inner = ctk.CTkFrame(f, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(inner, text="Choose format:", font=theme.FONT_BOLD, text_color=theme.TEXT).pack(anchor="w", pady=(0,6))
        fmt = tk.StringVar(value="excel")
        for val, lbl in [("excel", "Excel (.xlsx)"), ("csv", "CSV / Access"), ("pdf", "PDF"), ("word", "Word (.doc)")]:
            ctk.CTkRadioButton(inner, text=lbl, variable=fmt, value=val).pack(anchor="w", pady=2)
        def _go():
            v = fmt.get()
            if v == "excel": self._export_excel()
            elif v == "csv": self._export_csv()
            elif v == "pdf": self._export_pdf()
            elif v == "word": self._export_word()
        ctk.CTkButton(inner, text="Export", width=120, fg_color=theme.ACCENT, command=_go).pack(anchor="w", pady=(10,0))

    def _view_backup(self):
        f = self.overview_content
        f.grid_rowconfigure(0, weight=1)
        inner = ctk.CTkFrame(f, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew")
        ctk.CTkButton(inner, text="Backup now", width=140, command=self._backup_now).pack(anchor="w", pady=4)
        ctk.CTkButton(inner, text="Restore backup...", width=140, command=self._restore_backup).pack(anchor="w", pady=4)

    def _view_calendar(self):
        import datetime as _dt
        f = self.overview_content
        f.grid_rowconfigure(1, weight=0)
        # month navigation
        nav = ctk.CTkFrame(f, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._cal_year = getattr(self, "_cal_year", _dt.date.today().year)
        self._cal_month = getattr(self, "_cal_month", _dt.date.today().month)

        def _render():
            for w in grid.winfo_children():
                w.destroy()
            import calendar as _cal
            title_lbl.configure(text="%s %d" % (_cal.month_name[self._cal_month], self._cal_year))
            # weekday headers
            for i, wd in enumerate(["L", "Ma", "Mi", "J", "V", "S", "D"]):
                ctk.CTkLabel(grid, text=wd, font=theme.FONT_BOLD, text_color=theme.MUTED).grid(row=0, column=i, padx=2, pady=2)
            cal = _cal.Calendar(firstweekday=0)
            weeks = cal.monthdayscalendar(self._cal_year, self._cal_month)
            apps = db.list_appointments()
            by_day = {}
            for a in apps:
                try:
                    d = _dt.datetime.strptime(a["datetime"], "%d.%m.%Y %H:%M") if " " in a["datetime"] else _dt.datetime.strptime(a["datetime"], "%d.%m.%Y")
                except Exception:
                    continue
                if d.year == self._cal_year and d.month == self._cal_month:
                    by_day.setdefault(d.day, []).append(a)
            for wi, week in enumerate(weeks, start=1):
                for di, day in enumerate(week):
                    if day == 0:
                        continue
                    txt = str(day)
                    if day in by_day:
                        txt += " \u2022%d" % len(by_day[day])
                    btn = ctk.CTkButton(grid, text=txt, width=44, height=32,
                                        fg_color=theme.SELECTED if day in by_day else "transparent",
                                        text_color=theme.TEXT, hover_color=theme.ACCENT_LIGHT,
                                        command=lambda d=day: self._show_day_appointments(d))
                    btn.grid(row=wi, column=di, padx=2, pady=2)

        def _prev():
            if self._cal_month == 1:
                self._cal_month = 12
                self._cal_year -= 1
            else:
                self._cal_month -= 1
            _render()

        def _next():
            if self._cal_month == 12:
                self._cal_month = 1
                self._cal_year += 1
            else:
                self._cal_month += 1
            _render()

        ctk.CTkButton(nav, text="\u2190", width=36, command=_prev).pack(side="left", padx=2)
        title_lbl = ctk.CTkLabel(nav, text="", font=theme.FONT_TITLE, text_color=theme.TEXT)
        title_lbl.pack(side="left", padx=12)
        ctk.CTkButton(nav, text="\u2192", width=36, command=_next).pack(side="left", padx=2)
        ctk.CTkButton(nav, text=lang.t("ui_new_appointment"), width=140, fg_color=theme.ACCENT,
                      command=self._nav_new_appointment).pack(side="right", padx=2)

        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="nsew", pady=4)
        _render()

        # --- new-appointment form directly under the calendar
        self._cal_selected_day = getattr(self, "_cal_selected_day", None) or datetime.date.today().day
        try:
            import calendar as _cal3
            max_day = _cal3.monthrange(self._cal_year, self._cal_month)[1]
            self._cal_selected_day = min(int(self._cal_selected_day), max_day)
        except Exception as e:
            log.debug_exc(logger)
        form = ctk.CTkFrame(f, fg_color=theme.PANEL, corner_radius=getattr(theme, "CARD_RADIUS", 8),
                            border_width=1, border_color=getattr(theme, "BORDER", theme.MUTED))
        form.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        form.grid_columnconfigure(1, weight=1)
        self._cal_form_date = ctk.CTkLabel(form, text="", font=theme.FONT_BOLD, text_color=theme.TEXT, anchor="w")
        self._cal_form_date.grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(8, 2))
        self._cal_form_date.configure(text="%s \u2013 %02d.%02d.%d" % (
            lang.t("ui_new_appointment"), self._cal_selected_day, self._cal_month, self._cal_year))

        ctk.CTkLabel(form, text=lang.t("ui_patient") + ":", font=theme.FONT_SMALL,
                     text_color=theme.MUTED).grid(row=1, column=0, sticky="w", padx=8)
        patients = {}
        try:
            for p in db.get_all_patients():
                patients[p["name"]] = p
        except Exception as e:
            log.debug_exc(logger)
        self._cal_patients = patients
        names = sorted(patients.keys())
        self._cal_pat_var = ctk.StringVar(value=(names[0] if names else "\u2014"))
        ctk.CTkOptionMenu(form, values=names if names else ["\u2014"], variable=self._cal_pat_var,
                          width=170).grid(row=1, column=1, columnspan=3, sticky="w", padx=8, pady=2)

        ctk.CTkLabel(form, text=lang.t("ui_time"), font=theme.FONT_SMALL,
                     text_color=theme.MUTED).grid(row=2, column=0, sticky="w", padx=8)
        self._cal_time_var = ctk.StringVar(value="09:00")
        ctk.CTkEntry(form, textvariable=self._cal_time_var, width=80,
                     justify="center").grid(row=2, column=1, sticky="w", padx=8, pady=2)
        ctk.CTkLabel(form, text=lang.t("ui_duration_min"), font=theme.FONT_SMALL,
                     text_color=theme.MUTED).grid(row=2, column=2, sticky="e")
        self._cal_dur_var = ctk.StringVar(value="30")
        ctk.CTkEntry(form, textvariable=self._cal_dur_var, width=60,
                     justify="center").grid(row=2, column=3, sticky="w", padx=(2, 8), pady=2)

        ctk.CTkLabel(form, text=lang.t("ui_status") + ":", font=theme.FONT_SMALL,
                     text_color=theme.MUTED).grid(row=3, column=0, sticky="w", padx=8)
        self._cal_status_var = ctk.StringVar(value="scheduled")
        ctk.CTkOptionMenu(form, values=list(db.SESSION_STATUSES), variable=self._cal_status_var,
                          width=140).grid(row=3, column=1, columnspan=3, sticky="w", padx=8, pady=2)

        ctk.CTkLabel(form, text=lang.t("ui_notes") + ":", font=theme.FONT_SMALL,
                     text_color=theme.MUTED).grid(row=4, column=0, sticky="nw", padx=8)
        self._cal_notes_entry = ctk.CTkEntry(form, placeholder_text=lang.t("ui_notes"))
        self._cal_notes_entry.grid(row=4, column=1, columnspan=3, sticky="ew", padx=8, pady=2)

        ctk.CTkButton(form, text=lang.t("ui_add_appointment"), fg_color=theme.ACCENT,
                      command=self._cal_add_appointment).grid(row=5, column=0, columnspan=4,
                                                              sticky="ew", padx=8, pady=(6, 2))
        self._cal_err = ctk.CTkLabel(form, text="", font=theme.FONT_SMALL, text_color="#c0392b", anchor="w")
        self._cal_err.grid(row=6, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 8))

    def _cal_add_appointment(self):
        try:
            self._cal_err.configure(text="")
        except Exception as e:
            log.debug_exc(logger)
        try:
            p = getattr(self, "_cal_patients", {}).get(self._cal_pat_var.get())
            if p is None:
                self._cal_err.configure(text=lang.t("ui_pick_patient"))
                return
            hh = mm = None
            try:
                parts = self._cal_time_var.get().strip().replace(".", ":").split(":")
                if len(parts) == 2:
                    hh, mm = int(parts[0]), int(parts[1])
            except ValueError:
                log.debug_exc(logger)
            if hh is None or not (0 <= hh < 24 and 0 <= mm < 60):
                self._cal_err.configure(text=lang.t("ui_invalid_time"))
                return
            try:
                dur = max(5, int(self._cal_dur_var.get()))
            except ValueError:
                log.debug_exc(logger)
                dur = 30
            day = getattr(self, "_cal_selected_day", datetime.date.today().day)
            dt = "%02d.%02d.%d %02d:%02d" % (day, self._cal_month, self._cal_year, hh, mm)
            db.add_appointment(p["id"], dt, duration_min=dur, status=self._cal_status_var.get(),
                               notes=self._cal_notes_entry.get().strip())
            self._show_view("calendar")
            self._show_day_appointments(day)
        except Exception as e:
            log.debug_exc(logger)
            try:
                self._cal_err.configure(text=str(e))
            except Exception:
                pass

    def _show_day_appointments(self, day):
        """Open the schedule for a calendar day in the right preview panel (no popups)."""
        date_str = "%02d.%02d.%d" % (day, self._cal_month, self._cal_year)
        self._cal_selected_day = day
        if getattr(self, "_cal_form_date", None) is not None:
            try:
                if self._cal_form_date.winfo_exists():
                    self._cal_form_date.configure(text="%s \u2013 %s" % (lang.t("ui_new_appointment"), date_str))
            except Exception as e:
                log.debug_exc(logger)
        # leaving any open patient file: save it first, then swap the preview
        try:
            self._save_open_files()
        except Exception as e:
            log.debug_exc(logger)
        self.selected_patient_id = None
        self.patient_panels = {}
        self._current_panel = None
        for w in self.file_host.winfo_children():
            w.destroy()

        root = ctk.CTkFrame(self.file_host, fg_color="transparent")
        root.place(relx=0, rely=0, relwidth=1, relheight=1, x=0)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        # --- header: date + close
        head = ctk.CTkFrame(root, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=theme.PADDING, pady=(theme.PADDING, 4))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text=date_str, font=theme.FONT_TITLE, text_color=theme.TEXT,
                     anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkButton(head, text="\u2715", width=30,
                      command=self._show_placeholder).grid(row=0, column=1, padx=(8, 0))

        # --- scrollable list of appointment cards
        lst = ctk.CTkScrollableFrame(root, fg_color="transparent")
        lst.grid(row=1, column=0, sticky="nsew", padx=theme.PADDING)
        lst.grid_columnconfigure(0, weight=1)
        try:
            utils._patch_scrollable(lst)
        except Exception as e:
            log.debug_exc(logger)

        def _render_list():
            for w in lst.winfo_children():
                w.destroy()
            apps = []
            for a in db.list_appointments():
                try:
                    d = datetime.datetime.strptime(a["datetime"].split(" ")[0], "%d.%m.%Y")
                except Exception:
                    log.debug_exc(logger)
                    continue
                if d.day == day and d.month == self._cal_month and d.year == self._cal_year:
                    apps.append(a)
            apps.sort(key=lambda a: (a["datetime"].split(" ")[1] if " " in a["datetime"] else "99:99", a["id"]))
            if not apps:
                ctk.CTkLabel(lst, text=lang.t("ui_no_appointments"), font=theme.FONT_SUB,
                             text_color=theme.MUTED, anchor="w").grid(row=0, column=0, sticky="w", padx=4, pady=10)
                return
            pmap = {}
            try:
                for p in db.get_all_patients():
                    pmap[p["id"]] = p["name"]
            except Exception as e:
                log.debug_exc(logger)
            for i, a in enumerate(apps):
                card = ctk.CTkFrame(lst, fg_color=theme.PANEL, corner_radius=6,
                                    border_width=1, border_color=getattr(theme, "BORDER", theme.MUTED))
                card.grid(row=i, column=0, sticky="ew", padx=2, pady=3)
                card.grid_columnconfigure(1, weight=1)
                time_str = a["datetime"].split(" ")[1] if " " in a["datetime"] else "--:--"
                ctk.CTkLabel(card, text=time_str, font=theme.FONT_BOLD, text_color=theme.ACCENT,
                             width=60, anchor="w").grid(row=0, column=0, padx=(10, 4), pady=6)
                name = pmap.get(a["patient_id"], "?")
                ctk.CTkLabel(card, text=name, font=theme.FONT_BODY, text_color=theme.TEXT,
                             anchor="w").grid(row=0, column=1, sticky="w", padx=2)
                ctk.CTkLabel(card, text="%d min" % (a.get("duration_min") or 0),
                             font=theme.FONT_SMALL, text_color=theme.MUTED, width=60).grid(row=0, column=2, padx=2)
                st_var = ctk.StringVar(value=a.get("status", "scheduled"))

                def _set_status(v, aid=a["id"]):
                    db.update_appointment(aid, status=v)
                    _render_list()
                    self._show_view("calendar")

                ctk.CTkOptionMenu(card, values=list(db.SESSION_STATUSES), variable=st_var,
                                  width=110, command=lambda v, f=_set_status: f(v)).grid(row=0, column=3, padx=4)

                def _del(btn, aid=a["id"]):
                    if btn.cget("text") != "\u2713":
                        btn.configure(text="\u2713", fg_color="#c0392b")
                        return
                    db.delete_appointment(aid)
                    _render_list()
                    self._show_view("calendar")

                del_btn = ctk.CTkButton(card, text="\u2715", width=30, fg_color="transparent",
                                        border_width=1, border_color=getattr(theme, "BORDER", theme.MUTED),
                                        text_color=theme.MUTED, hover_color="#c0392b")
                # wire two-step confirm without popups: first click arms the button
                del_btn.configure(command=lambda b=del_btn: _del(b))
                del_btn.grid(row=0, column=4, padx=(0, 8))

        _render_list()

    def _nav_new_appointment(self):
        t = datetime.date.today()
        self._cal_year, self._cal_month = t.year, t.month
        self._cal_selected_day = t.day
        self._show_view("calendar")
        self._show_day_appointments(t.day)

    def _view_new_patient(self):
        self._open_patient_by_id(None)
        self._show_view("patients")



    def _show_placeholder(self):
        for w in self.file_host.winfo_children():
            w.destroy()
        lbl = ctk.CTkLabel(self.file_host, text=lang.t("ui_select_patient_file"),
                           font=theme.FONT_SUB, text_color=theme.MUTED)
        lbl.place(relx=0.5, rely=0.5, anchor="center")

    def refresh_patients_db(self):
        self._search_job = None
        card_list = getattr(self, "card_list", None)
        try:
            if card_list is None or not card_list.winfo_exists():
                return
        except Exception:
            return
        try:
            _canvas = card_list._parent_canvas
            _yview = _canvas.yview()
        except Exception:
            _canvas = None
            _yview = None
        for w in card_list.winfo_children():
            w.destroy()
        self._visible_patient_ids = []
        self._card_widgets = {}
        try:
            patients = db.get_all_patients(sort_by=self.sort_by, sort_dir=self.sort_dir)
            search_raw = ""
            entry = getattr(self, "search_entry", None)
            try:
                if entry is not None and entry.winfo_exists():
                    search_raw = entry.get()
            except Exception:
                search_raw = ""
            if not search_raw:
                search_raw = getattr(self, "_search_text", "") or ""
            search = _norm(search_raw)
            scope = getattr(self, "search_scope", "everything")
            scope = scope.lower() if isinstance(scope, str) else "everything"
            shown = 0
            for p in patients:
                diag_text = p.get('diagnostic', '') or ''
                first_line = utils._strip_inline_formatting(diag_text).split(chr(10))[0] if diag_text else ''
                if scope == "name":
                    haystack = _norm(p.get('name', ''))
                else:
                    haystack = _norm(" ".join([str(p.get('name','')), str(p.get('localitate','')), diag_text,
                                               p.get('objective','') or '', p.get('evaluation','') or '',
                                               p.get('observation','') or '']))
                if search and search not in haystack:
                    continue
                shown += 1
                self._visible_patient_ids.append(p.get('id'))
                self._build_patient_card(p, first_line, (p.get('id') == self.selected_patient_id))
            if hasattr(self, "count_label"):
                if search:
                    count_text = lang.t("overview_count", n=shown, total=len(patients))
                else:
                    count_text = lang.t("overview_count_all", n=shown)
                try:
                    count_text += "  \u00b7  " + self._sort_label()
                except Exception as e:
                    log.debug_exc(logger)
                self.count_label.configure(text=count_text)
            if not patients:
                self._show_list_empty(lang.t("empty_no_patients"))
            elif not self._visible_patient_ids:
                self._show_list_empty(lang.t("empty_no_match", q=search_raw.strip()))
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))
        try:
            if "_canvas" in locals() and _canvas is not None and "_yview" in locals() and _yview is not None:
                _canvas.yview_moveto(_yview[0])
        except Exception as e:
            log.debug_exc(logger)
    def _show_list_empty(self, text):
        try:
            ctk.CTkLabel(self.card_list, text=text, font=theme.FONT_SMALL, text_color=theme.MUTED,
                         wraplength=280, justify="left").pack(anchor="w", padx=10, pady=12)
        except Exception as e:
            log.debug_exc(logger)
    def _build_patient_card(self, p, first_line, selected):
        card = ctk.CTkFrame(self.card_list, fg_color=theme.SELECTED if selected else theme.PANEL,
                            corner_radius=theme.CARD_RADIUS, border_width=1, border_color=theme.BORDER)
        card.pack(fill="x", pady=1)
        card.grid_columnconfigure(1, weight=1)

        av = ctk.CTkLabel(card, text=_initials(p.get('name','')), width=theme.AVATAR_SIZE, height=theme.AVATAR_SIZE,
                          corner_radius=theme.AVATAR_SIZE // 2, fg_color=theme.ACCENT, text_color="white",
                          font=ctk.CTkFont(size=12, weight="bold"))
        av.grid(row=0, column=0, rowspan=3, padx=8, pady=1)

        name_lbl = ctk.CTkLabel(card, text=p.get('name',''), font=theme.FONT_BOLD, text_color=theme.TEXT, anchor="w")
        name_lbl.grid(row=0, column=1, sticky="w", pady=(2, 0))

        meta = ctk.CTkLabel(card, text=p.get('localitate','') or "\u2014", font=theme.FONT_SMALL, text_color=theme.CARD_META, anchor="w")
        meta.grid(row=1, column=1, sticky="w")

        preview = ctk.CTkLabel(card, text=(first_line[:50] + ("..." if len(first_line) > 50 else "")) or "No diagnostic",
                               font=theme.FONT_SMALL, text_color=theme.CARD_META, anchor="w")
        preview.grid(row=2, column=1, sticky="w", pady=(0, 2))

        if selected:
            open_btn = ctk.CTkButton(card, text=lang.t("ui_open_file") + " \u203A", width=80, height=24, corner_radius=8,
                                     fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK, font=theme.FONT_SMALL,
                                     command=lambda pid=p['id']: self._open_patient_by_id(pid))
            open_btn.grid(row=0, column=2, rowspan=3, padx=10)
        else:
            open_btn = ctk.CTkButton(card, text=lang.t("ui_open_file") + " \u203A", width=80, height=24, corner_radius=8,
                                     fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK, font=theme.FONT_SMALL,
                                     command=lambda pid=p['id']: self._open_patient_by_id(pid))
            open_btn.grid(row=0, column=2, rowspan=3, padx=10)
            open_btn.grid_remove()

        try:
            try:
                card.configure(takefocus=True)
            except Exception:
                # CTkFrame doesn't accept takefocus; route to the inner tk frame
                try:
                    card._canvas.configure(takefocus=True)
                except Exception:
                    log.debug_exc(logger)
        except Exception as e:
            log.debug_exc(logger)
        card.bind("<Return>", lambda e=None, pid=p['id']: self._open_patient_by_id(pid))
        card.bind("<space>", lambda e=None, pid=p['id']: self._open_patient_by_id(pid))
        card.bind("<Down>", lambda e=None: (self._navigate_patient(1), "break")[1])
        card.bind("<Up>", lambda e=None: (self._navigate_patient(-1), "break")[1])
        for w in (card, av, name_lbl, meta, preview):
            w.bind("<Button-1>", lambda e=None, pid=p['id']: self._open_patient_by_id(pid))
            w.bind("<Button-3>", lambda e=None, pid=p['id']: self._card_context(e, pid))

        self._card_widgets[p.get('id')] = (card, open_btn)

    def _card_context(self, event, pid):
        if event is None:
            return
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
                    except Exception as e:
                        log.debug_exc(logger)
                deleted_row_id = db.delete_patient(pid)
                if deleted_row_id is not None:
                    self._last_deleted_row_id = deleted_row_id
                    self._last_deleted_name = None
                    try:
                        # fetch name from deleted row
                        for d in db.list_deleted():
                            if d.get('id') == deleted_row_id:
                                self._last_deleted_name = d.get('name')
                                break
                    except Exception as e:
                        log.debug_exc(logger)
                if self.selected_patient_id == pid:
                    self.selected_patient_id = None
                    self._show_placeholder()
                self.refresh_patients_db()
                self._show_undo_hint()
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _show_status_banner(self, text):
        """Show a short status message at the bottom of the overview panel."""
        try:
            banner = ctk.CTkLabel(self.overview_content, text=text, fg_color=theme.ACCENT,
                                  text_color="white", corner_radius=6, font=theme.FONT_SMALL,
                                  padx=10, pady=4)
            banner.place(relx=0.5, rely=1.0, anchor="s", y=-8)
            banner.lift()
            self.after(4000, lambda b=banner: (b.destroy() if utils._exists(b) else None))
        except Exception as e:
            log.debug_exc(logger)
    def _show_undo_hint(self):
        """Show a short, non-blocking 'Ctrl+Z to undo' banner after a delete."""
        name = getattr(self, "_last_deleted_name", None) or "patient"
        try:
            hint = ctk.CTkLabel(self.overview_content,
                                text=lang.t("ui_deleted_patient", name=str(name)) + " \u00b7 " + lang.t("ui_ctrl_z_undo"),
                                fg_color=theme.DANGER, text_color="white", corner_radius=6,
                                font=theme.FONT_SMALL, padx=10, pady=4)
            hint.place(relx=0.5, rely=1.0, anchor="s", y=-46)
            hint.lift()
            self._undo_hint = hint
            self.after(6000, lambda: hint.destroy() if utils._exists(hint) else None)
        except Exception as e:
            log.debug_exc(logger)
    def _handle_ctrl_z(self, event=None):
        w = self.focus_get()
        if isinstance(w, tk.Text):
            try:
                w.event_generate("<<Undo>>")
            except Exception as e:
                log.debug_exc(logger)
            return "break"
        self._undo_last_delete(event)
        return "break"

    def _handle_ctrl_y(self, event=None):
        w = self.focus_get()
        if isinstance(w, tk.Text):
            try:
                w.event_generate("<<Redo>>")
            except Exception as e:
                log.debug_exc(logger)
            return "break"
        return "break"

    def _undo_last_delete(self, event=None):
        row_id = getattr(self, "_last_deleted_row_id", None)
        if row_id is None:
            return
        try:
            hint = getattr(self, "_undo_hint", None)
            if hint is not None:
                try:
                    if hint.winfo_exists():
                        hint.destroy()
                except Exception as e:
                    log.debug_exc(logger)
                self._undo_hint = None
            new_pid = db.restore_deleted(row_id)
            self._last_deleted_row_id = None
            self._last_deleted_name = None
            self.refresh_patients_db()
            if new_pid is not None:
                self._open_patient_by_id(new_pid)
            messagebox.showinfo(lang.t("app_name"), lang.t("ui_restore_patient"))
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))
        return "break"

    def _copy_name_by_id(self, pid):
        p = db.get_patient(patient_id=pid)
        if p:
            self.clipboard_clear()
            self.clipboard_append(p.get('name', ''))

    def _save_open_files(self):
        """Persist unsaved edits in open patient files before switching away or exiting."""
        for pid, panel in list(getattr(self, "patient_panels", {}).items()):
            try:
                if panel.winfo_exists():
                    panel.save_if_dirty()
            except Exception as e:
                log.debug_exc(logger)
    def _set_selected_card(self, pid):
        """Toggle the selected highlight without rebuilding the card list."""
        card_list = getattr(self, "card_list", None)
        _canvas = None
        _yview = None
        try:
            if card_list is not None and card_list.winfo_exists():
                _canvas = card_list._parent_canvas
                _yview = _canvas.yview()
        except Exception as e:
            log.debug_exc(logger)
        for cid, (card, btn) in list(getattr(self, "_card_widgets", {}).items()):
            try:
                if cid == pid:
                    card.configure(fg_color=theme.SELECTED)
                    btn.grid()
                else:
                    card.configure(fg_color=theme.PANEL)
                    btn.grid_remove()
            except Exception as e:
                log.debug_exc(logger)
        try:
            if _canvas is not None and _yview is not None:
                def _restore_scroll():
                    try:
                        if _canvas.winfo_exists():
                            _canvas.yview_moveto(_yview[0])
                    except Exception as e:
                        log.debug_exc(logger)
                self.after_idle(_restore_scroll)
        except Exception as e:
            log.debug_exc(logger)
    def _open_patient_by_id(self, patient_id):
        # warn before discarding an unsaved new patient
        for pid, panel in list(getattr(self, "patient_panels", {}).items()):
            if getattr(panel, "_is_new", False) and getattr(panel, "_dirty", False):
                if not messagebox.askyesno(lang.t("app_name"), "Discard unsaved new patient?"):
                    return
        if patient_id is None:
            self._save_open_files()
            for w in self.file_host.winfo_children():
                w.destroy()
            self.patient_panels = {}
            panel = PatientFilePanel(self.file_host, None, on_close=self.refresh_patients_db, new=True)
            panel.place(relx=0, rely=0, relwidth=1, relheight=1, x=0)
            self.patient_panels[None] = panel
            self.selected_patient_id = None
            self._show_placeholder() if False else None
            return
        self._save_open_files()
        self.selected_patient_id = patient_id
        for w in self.file_host.winfo_children():
            w.destroy()
        self.patient_panels = {}
        panel = PatientFilePanel(self.file_host, patient_id, on_close=self.refresh_patients_db)
        # show immediately (no slide-in clip)
        panel.place(relx=0, rely=0, relwidth=1, relheight=1, x=0)
        self.patient_panels[patient_id] = panel
        self._set_selected_card(patient_id)


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

    def _search_patients_dialog(self):
        try:
            import tkinter.simpledialog as _sd
            term = _sd.askstring("Search patients", "Search patients:", initialvalue=getattr(self, "_search_text", ""),
                                 parent=self)
        except Exception:
            term = None
        if term is None:
            return
        self._search_text = term.strip()
        self.refresh_patients_db()

    def _clear_search(self):
        try:
            if getattr(self, "search_entry", None) is not None and self.search_entry.winfo_exists():
                self.search_entry.delete(0, "end")
        except Exception as e:
            log.debug_exc(logger)
        self._search_text = ""
        self.refresh_patients_db()

    def _set_ui_scale(self, scale):
        try:
            ctk.set_widget_scaling(scale)
            ctk.set_window_scaling(scale)
        except Exception as e:
            log.debug_exc(logger)
        try:
            data = load_settings()
            data["ui_scale"] = scale
            save_settings(data)
        except Exception as e:
            log.debug_exc(logger)
    def _toggle_theme(self):
        cur = ctk.get_appearance_mode()
        new_mode = "Dark" if cur == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        try:
            theme.set_appearance(new_mode)
        except Exception as e:
            log.debug_exc(logger)
        if theme.base() == "medidash":
            self._rebuild_ui()
        try:
            data = load_settings()
            data["appearance"] = new_mode
            save_settings(data)
        except Exception as e:
            log.debug_exc(logger)
    def _rebuild_ui(self):
        self._save_open_files()
        view = getattr(self, "_current_view", "patients")
        pid = self.selected_patient_id
        search_text = getattr(self, "_search_text", "")
        search_scope = getattr(self, "_search_scope_text", "everything")
        for w in (getattr(self, "_header", None), getattr(self, "_sidebar", None), getattr(self, "_content", None)):
            try:
                if w is not None and w.winfo_exists():
                    w.destroy()
            except Exception as e:
                log.debug_exc(logger)
        self._header = None
        self._sidebar = None
        self._content = None
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self._build_header_bar()
        self._build_sidebar()
        self._build_content()
        self._search_text = search_text
        self._search_scope_text = search_scope
        try:
            self._show_view(view if view else "patients")
        except Exception:
            self._show_view("patients")
        if pid is not None:
            try:
                self._open_patient_by_id(pid)
            except Exception as e:
                log.debug_exc(logger)
        self._sidebar_visible = True
        try:
            self._on_configure_responsive()
        except Exception as e:
            log.debug_exc(logger)
    def _show_account_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Language: " + lang.get_language().upper())
        menu.add_command(label="Toggle light/dark", command=self._toggle_theme)
        menu.add_separator()
        menu.add_command(label="Theme: Classic", command=lambda: self._apply_ui_theme("classic"))
        menu.add_command(label="Theme: MediDashboard", command=lambda: self._apply_ui_theme("medidash"))
        menu.add_separator()
        menu.add_command(label="Keyboard shortcuts", command=self._show_shortcuts)
        menu.add_command(label="About", command=lambda: messagebox.showinfo(lang.t("app_name"),
                                                                         "Patient Database\nVersion " + __version__ + "\nSQLite-backed patient records."))
        try:
            btn = getattr(self, "_account_btn", None)
            x = btn.winfo_rootx() if (btn is not None and btn.winfo_exists()) else self.winfo_rootx()
            y = (btn.winfo_rooty() + btn.winfo_height()) if (btn is not None and btn.winfo_exists()) else self.winfo_rooty()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception as e:
                log.debug_exc(logger)
    def _apply_appearance(self, mode):
        mode = "Dark" if str(mode).lower().startswith("d") else "Light"
        ctk.set_appearance_mode(mode)
        try:
            theme.set_appearance(mode)
        except Exception as e:
            log.debug_exc(logger)
        if theme.base() == "medidash":
            self._rebuild_ui()
        try:
            data = load_settings()
            data["appearance"] = mode
            save_settings(data)
        except Exception as e:
            log.debug_exc(logger)
    def _apply_ui_theme(self, name):
        if name not in ("classic", "medidash"):
            name = "classic"
        self._save_open_files()
        try:
            data = load_settings()
            data["ui_theme"] = name
            save_settings(data)
        except Exception as e:
            log.debug_exc(logger)
        theme.set_theme(name)
        self._rebuild_ui()

    def _show_account_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Language: " + lang.get_language().upper())
        menu.add_command(label="Toggle light/dark", command=self._toggle_theme)
        menu.add_separator()
        menu.add_command(label="Theme: Classic", command=lambda: self._apply_ui_theme("classic"))
        menu.add_command(label="Theme: MediDashboard", command=lambda: self._apply_ui_theme("medidash"))
        menu.add_separator()
        menu.add_command(label="Keyboard shortcuts", command=self._show_shortcuts)
        menu.add_command(label="About", command=lambda: messagebox.showinfo(lang.t("app_name"),
                                                                         "Patient Database\nVersion " + __version__ + "\nSQLite-backed patient records."))
        try:
            btn = getattr(self, "_account_btn", None)
            x = btn.winfo_rootx() if (btn is not None and btn.winfo_exists()) else self.winfo_rootx()
            y = (btn.winfo_rooty() + btn.winfo_height()) if (btn is not None and btn.winfo_exists()) else self.winfo_rooty()
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception as e:
                log.debug_exc(logger)
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
            self._show_status_banner(lang.t("status_exported_csv"))
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
        except Exception as e:
            log.debug_exc(logger)
        self.refresh_patients_db()

    SORT_LABELS = [("name", "Name"), ("updated", "Last modified"),
                   ("localitate", "Locality"), ("created", "Created")]

    def _sort_label(self):
        label = dict(self.SORT_LABELS).get(self.sort_by, "Name")
        return label + (" \u2191" if self.sort_dir == "asc" else " \u2193")

    def _show_sort_menu(self):
        menu = tk.Menu(self, tearoff=0)
        for key, label in self.SORT_LABELS:
            mark = " \u2713" if self.sort_by == key else ""
            menu.add_command(label=label + mark, command=lambda k=key: self._sort_by(k))
        menu.add_separator()
        menu.add_command(label="Ascending" + (" \u2713" if self.sort_dir == "asc" else ""),
                         command=lambda: self._set_sort_dir("asc"))
        menu.add_command(label="Descending" + (" \u2713" if self.sort_dir == "desc" else ""),
                         command=lambda: self._set_sort_dir("desc"))
        try:
            x = self.sort_btn.winfo_rootx()
            y = self.sort_btn.winfo_rooty() + self.sort_btn.winfo_height()
            menu.tk_popup(x, y)
        except Exception as e:
            log.debug_exc(logger)
        finally:
            try:
                menu.grab_release()
            except Exception as e:
                log.debug_exc(logger)
    def _set_sort_dir(self, direction):
        if direction == self.sort_dir:
            return
        self.sort_dir = direction
        try:
            data = load_settings()
            data["sort_by"] = self.sort_by
            data["sort_dir"] = self.sort_dir
            save_settings(data)
        except Exception as e:
            log.debug_exc(logger)
        self.refresh_patients_db()

    def _show_context_menu(self, event):
        """Right-click context menu for the patient card list."""
        if event is None:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Open", command=self._open_patient_file)
        menu.add_command(label="Edit patient", command=self._edit_current_patient)
        menu.add_command(label="Copy name", command=self._copy_current_name)
        menu.add_separator()
        menu.add_command(label="Delete", command=self._delete_patient_db)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception as e:
                log.debug_exc(logger)
    def _edit_current_patient(self):
        panel = getattr(self, "patient_panels", {}).get(self.selected_patient_id)
        if panel is not None and panel.winfo_exists():
            panel._edit_patient_info()
        elif self.selected_patient_id is not None:
            self._open_patient_by_id(self.selected_patient_id)
            panel = self.patient_panels.get(self.selected_patient_id)
            if panel is not None and panel.winfo_exists():
                panel._edit_patient_info()

    def _copy_current_name(self):
        if self.selected_patient_id is None:
            return
        p = db.get_patient(patient_id=self.selected_patient_id)
        if p:
            self.clipboard_clear()
            self.clipboard_append(p.get('name', ''))

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
            # remember last selection
            import json as _json
            settings = load_settings()
            initial = settings.get("export_fields")
            if not initial:
                initial = [k for k, _ in EXPORT_FIELDS]
            dlg = ExportFieldsDialog(self, EXPORT_FIELDS, initial=initial)
            self.wait_window(dlg)
            if not dlg.result:
                return
            chosen = dlg.result
            # persist
            settings["export_fields"] = chosen
            save_settings(settings)

            path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="Save as Excel")
            if not path:
                return
            wb = Workbook()
            ws = wb.active
            ws.title = "Pacienti"
            headers = [h for k, h in EXPORT_FIELDS if k in chosen]
            ws.append(headers)
            for c in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=c)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="4472C4")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            patients = db.get_all_patients()
            for i, p in enumerate(patients, 1):
                ws.append([_field_value(p, k, i) for k in chosen])
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
            for idx in range(1, len(headers) + 1):
                ws.column_dimensions[chr(64 + idx)].width = 18
            ws.freeze_panes = "A2"
            wb.save(path)
            self._show_status_banner(lang.t("ui_export_excel_ok"))
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
            self._show_status_banner(lang.t("ui_export_ok"))
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
            self._show_status_banner(lang.t("status_exported_word"))
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _backup_now(self):
        try:
            import shutil, datetime
            folder = os.path.join(_base_dir(), "backup")
            os.makedirs(folder, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(folder, "patients_" + stamp + ".db")
            shutil.copy2(db.db_path(), dest)
            ok, info = db.verify_backup(dest)
            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".db")]
            files.sort(key=os.path.getmtime)
            while len(files) > 7:
                try:
                    os.remove(files.pop(0))
                except OSError:
                    break
            if ok:
                messagebox.showinfo(lang.t("app_name"), "Backup created and verified (" + str(info) + " patients):\n" + dest)
            else:
                messagebox.showwarning(lang.t("app_name"), "Backup created but verification failed:\n" + str(info))
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _restore_backup(self):
        try:
            folder = os.path.join(_base_dir(), "backup")
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
                # ensure schema tables exist even if the backup predates a migration
                try:
                    db.init_db()
                except Exception:
                    pass
                self.refresh_patients_db()
                messagebox.showinfo(lang.t("app_name"), "Restore complete.")
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _import_data(self):
        try:
            db.pre_operation_backup("import")
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
                except Exception as e:
                    log.debug_exc(logger)
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
            folder = os.path.join(_base_dir(), "backup")
            os.makedirs(folder, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d")
            dest = os.path.join(folder, "patients_auto_" + stamp + ".db")
            if not os.path.exists(dest):
                shutil.copy2(db.db_path(), dest)
            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".db")]
            files.sort(key=os.path.getmtime)
            while len(files) > 7:
                try:
                    os.remove(files.pop(0))
                except OSError:
                    break
        except Exception as e:
            log.debug_exc(logger)
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



def main():
    try:
        ctk.deactivate_automatic_dpi_awareness()
    except Exception as e:
        log.debug_exc(logger)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
