"""Frontend: customtkinter GUI with Patient Database."""

import csv
import datetime
import functools
import glob
import importlib
import json
import os
import re
import shutil
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

import lang
import log
import theme
from error_ui import report_error
from services import export_service
from services.appointment_service import get_appointment_service
from services.backup_service import get_backup_service
from services.database_service import get_database_service
from services.patient_service import get_patient_service
from services.physio_service import SESSION_STATUSES
from ui import recolor, ttk_style
from version import __version__
from workers import BackgroundTask

logger = log.get_logger(__name__)


# ---------------------------------------------------------------------------
# Unhandled-exception reporting
# ---------------------------------------------------------------------------
# In a windowed exe there is no console, so Tkinter's default error output is
# lost.  These hooks write the traceback to app.log and to the Diagnostics
# list, and show the user one short dialog (at most once per minute).
_ERROR_DIALOG_INTERVAL = 60.0
_last_error_dialog = 0.0


def _is_benign_tcl_error(exc_type, exc_value):
    """Tk focus/destroy races during theme rebuilds are harmless."""
    name = getattr(exc_type, "__name__", str(exc_type))
    if "TclError" not in name:
        return False
    msg = str(exc_value).lower()
    if "bad window path name" in msg:
        return True
    if "invalid command name" in msg and "focus" in msg:
        return True
    return False


_GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)(?:([+-]\d+)([+-]\d+))?$")


def _clamp_geometry(geometry: str, screen_w: int, screen_h: int, min_visible: int = 120) -> str:
    """Clamp a restored window geometry so it cannot end up off-screen.

    ``geometry`` is a Tk geometry string such as ``1200x800+2400+100``.  The
    size is limited to the visible screen and the position is pulled back until
    at least ``min_visible`` pixels of the window remain reachable.  Strings
    that cannot be parsed are returned unchanged.
    """
    if not geometry:
        return geometry
    match = _GEOMETRY_RE.match(str(geometry).strip())
    if match is None:
        return geometry
    width = max(400, min(int(match.group(1)), max(400, int(screen_w))))
    height = max(300, min(int(match.group(2)), max(300, int(screen_h))))
    if match.group(3) is None or match.group(4) is None:
        return f"{width}x{height}"
    x = int(match.group(3))
    y = int(match.group(4))
    x = min(x, int(screen_w) - min_visible)
    x = max(x, min_visible - width)
    y = min(y, int(screen_h) - min_visible)
    y = max(y, min_visible - height)
    return f"{width}x{height}{x:+d}{y:+d}"


def _option_button(parent, text, active, command, width=90):
    """Settings button that shows whether its option is currently active."""
    return ctk.CTkButton(
        parent,
        text=text,
        width=width,
        fg_color=theme.ACCENT if active else theme.MUTED_BTN,
        hover_color=theme.ACCENT_DARK if active else theme.MUTED_BTN_HOVER,
        text_color=theme.ON_ACCENT,
        command=command,
    )


def _log_uncaught(exc_type, exc_value, exc_tb):
    logger.error("Unhandled exception: %s", exc_value, exc_info=(exc_type, exc_value, exc_tb))
    _write_crash_dump(exc_type, exc_value, exc_tb)


def _write_crash_dump(exc_type, exc_value, exc_tb):
    """Write a small crash_*.log (traceback + version + theme) for post-mortem."""
    try:
        import traceback as _tb

        folder = _data_dir()
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(folder, f"crash_{stamp}.log")
        lines = [
            "Crash report",
            "Time: " + datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "Version: " + __version__,
        ]
        try:
            lines.append("Theme: " + str(theme.active()))
        except Exception:
            pass
        try:
            lines.append("Appearance: " + str(getattr(theme, "_appearance", "")))
        except Exception:
            pass
        try:
            lines.append("Language: " + lang.get_language())
        except Exception:
            pass
        lines.append("")
        lines.append("".join(_tb.format_exception(exc_type, exc_value, exc_tb)))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        # keep only the newest few crash dumps
        try:
            dumps = sorted(
                f for f in os.listdir(folder) if f.startswith("crash_") and f.endswith(".log")
            )
            while len(dumps) > 5:
                try:
                    os.remove(os.path.join(folder, dumps.pop(0)))
                except OSError:
                    break
        except Exception:
            pass
    except Exception:
        log.debug_exc(logger)


def _show_crash_dialog(exc_value, owner=None):
    """Show an error dialog, throttled so a repeating failure cannot spam."""
    global _last_error_dialog
    now = time.monotonic()
    if now - _last_error_dialog < _ERROR_DIALOG_INTERVAL:
        return
    _last_error_dialog = now
    text = "{}\n\n{}\n\n{}".format(
        lang.t("ui_unexpected_error"), exc_value, lang.t("ui_error_details_hint")
    )
    try:
        if owner is not None:
            messagebox.showerror(lang.t("app_name"), text, parent=owner)
        else:
            messagebox.showerror(lang.t("app_name"), text)
    except Exception:
        log.debug_exc(logger)


def _excepthook(exc_type, exc_value, exc_tb):
    """Catch exceptions that escape the main thread."""
    if _is_benign_tcl_error(exc_type, exc_value):
        return
    _log_uncaught(exc_type, exc_value, exc_tb)
    _show_crash_dialog(exc_value)


def _thread_excepthook(args):
    """Catch exceptions that escape background threads."""
    if _is_benign_tcl_error(args.exc_type, args.exc_value):
        return
    _log_uncaught(args.exc_type, args.exc_value, args.exc_traceback)


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _data_dir() -> str:
    try:
        import paths

        return paths.app_data_dir()
    except Exception:
        return _base_dir()


def _asset_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return _base_dir()


def _prune_auto_backups(folder, keep=7):
    """Remove old automatic backups, but never touch safety copies.

    Only files created by the app (``patients_*.db``) are pruned.  Snapshots
    such as ``pre_migration_*.db`` / ``pre_purge_*.db`` are kept forever —
    deleting them used to destroy the only copy of real data.
    """
    try:
        files = [
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if name.startswith("patients_") and name.endswith(".db")
        ]
        files.sort(key=os.path.getmtime)
        while len(files) > keep:
            try:
                os.remove(files.pop(0))
            except OSError:
                break
    except Exception:
        log.debug_exc(logger)


import utils
from dialogs import (
    AddPatientDialog,
    ExportFieldsDialog,
    RestoreBackupDialog,
    SaveAsDialog,
    SettingsDialog,
    TrashDialog,
)
from tooltip import attach_tooltip, hide_tooltip
from ui.patient_panel import PatientFilePanel
from utils import (
    _initials,
    _norm,
)

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
    return os.path.join(_data_dir(), "settings.json")


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
            data["ui_theme"] = "medidash"
        if data.get("appearance") not in ("Light", "Dark"):
            data["appearance"] = "Light"
        if data.get("sort_by") not in (
            "name",
            "localitate",
            "diagnostic",
            "updated",
            "created",
            "nr",
        ):
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


def run_startup_checks() -> list[tuple[str, bool, str]]:
    """Validate the environment, database and bundled resources.

    Shared by the in-app Diagnostics view and the ``--self-test`` release
    smoke test, so both exercise exactly the same checks without creating a
    Tk window.
    """
    results: list[tuple[str, bool, str]] = []
    # database integrity
    try:
        ok = get_database_service().check_integrity()
        results.append(("Database integrity", ok, "OK" if ok else "FAILED"))
    except Exception as e:
        log.debug_exc(logger)
        results.append(("Database integrity", False, str(e)))
    # schema version
    try:
        v = get_database_service().schema_version()
        ok = v >= get_database_service().expected_schema_version
        results.append(
            (
                "Schema version",
                ok,
                (
                    "v%d" % v
                    if ok
                    else "v%d (expected %d)" % (v, get_database_service().expected_schema_version)
                ),
            )
        )
    except Exception as e:
        log.debug_exc(logger)
        results.append(("Schema version", False, str(e)))
    # schema / counts
    try:
        n = len(get_patient_service().list_patients())
        results.append(("Patients loaded", True, str(n)))
    except Exception as e:
        log.debug_exc(logger)
        results.append(("Patients loaded", False, str(e)))
    # settings parse
    try:
        s = load_settings()
        results.append(
            ("Settings", isinstance(s, dict), "OK" if isinstance(s, dict) else "invalid")
        )
    except Exception as e:
        log.debug_exc(logger)
        results.append(("Settings", False, str(e)))
    # assets
    try:
        logo = os.path.join(_asset_dir(), "assets", "logo.png")
        ok = os.path.exists(logo)
        results.append(("App assets", ok, "OK" if ok else "missing logo.png"))
    except Exception as e:
        log.debug_exc(logger)
        results.append(("App assets", False, str(e)))
    # backup folder writable
    try:
        folder = os.path.join(_data_dir(), "backup")
        os.makedirs(folder, exist_ok=True)
        test_path = os.path.join(folder, ".write_test")
        with open(test_path, "w") as fh:
            fh.write("ok")
        os.remove(test_path)
        results.append(("Backup folder", True, "writable"))
    except Exception as e:
        log.debug_exc(logger)
        results.append(("Backup folder", False, str(e)))
    # free disk
    try:
        free_gb = shutil.disk_usage(_data_dir()).free / (1024.0**3)
        ok = free_gb >= 0.1
        results.append(("Free disk", ok, f"{free_gb:.1f} GB"))
    except Exception as e:
        log.debug_exc(logger)
        results.append(("Free disk", False, str(e)))
    return results


class App(ctk.CTk):
    """Main application window: sidebar navigation, patient overview, and embedded patient file."""

    def __init__(self, patients_file=None):
        super().__init__()
        self._closing = False
        self._rebuilding = False
        self._ui_scale = 1.0
        self._lang_var = tk.StringVar(master=self, value=lang.get_language())
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        lang.set_language(load_language())
        self._lang_var.set(lang.get_language())
        self.title(lang.t("app_name"))
        self.minsize(1100, 700)
        # Restore window geometry / theme from settings
        try:
            settings = load_settings()
            try:
                scale = float(settings.get("ui_scale", 1.0))
            except (TypeError, ValueError):
                scale = 1.0
            if scale not in (1.0, 1.25, 1.5):
                scale = 1.0
            self._ui_scale = scale
            geom = settings.get("geometry")
            if geom:
                self.geometry(
                    _clamp_geometry(geom, self.winfo_screenwidth(), self.winfo_screenheight())
                )
            else:
                self.geometry("1200x800")
            mode = settings.get("appearance", "Light")
            try:
                ctk.set_widget_scaling(scale)
                ctk.set_window_scaling(scale)
            except Exception:
                log.debug_exc(logger)
            theme._appearance = mode
            ctk.set_appearance_mode(mode)
            theme.set_theme(settings.get("ui_theme", "medidash"))
        except Exception:
            self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)
        ttk_style.apply(self, scale=self._ui_scale)
        self._apply_window_icon()

        # Initialize database
        get_database_service().init()
        try:
            if not get_database_service().check_integrity():
                if messagebox.askyesno(
                    lang.t("app_name"),
                    lang.t("ui_restore_prompt"),
                ):
                    # find latest backup by modification time (not name)
                    folder = os.path.join(_data_dir(), "backup")
                    files = glob.glob(os.path.join(folder, "*.db"))
                    files = [
                        f
                        for f in files
                        if os.path.basename(f).startswith(("auto_", "pre_migration_", "pre_purge_"))
                    ]
                    if files:
                        latest = max(files, key=os.path.getmtime)
                        try:
                            shutil.copy2(latest, get_database_service().path())
                            # ensure schema tables exist even if the backup predates a migration
                            get_database_service().init()
                            messagebox.showinfo(
                                lang.t("app_name"),
                                lang.t("msg_restored_from", name=os.path.basename(latest)),
                            )
                        except Exception as e:
                            report_error(str(e))
        except Exception:
            log.debug_exc(logger)
        self._startup_checks = self._run_startup_checks()
        for _name, _ok, _detail in self._startup_checks:
            if not _ok:
                logger.warning("startup check failed: %s - %s", _name, _detail)
        self.patients_file = patients_file
        self.list_error = None
        try:
            self.known_patients = get_patient_service().get_patient_names()
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

        # Presentation-only status strip
        self._status_state = ""
        self._status_saved_at = ""
        self._patient_total = 0
        self._build_status_bar()

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
        # Menu accelerators that have no other binding yet.
        for sequence in ("<Control-Shift-S>", "<Control-Shift-s>"):
            self.bind(sequence, lambda e: (self._save_as(), "break")[1])
        for sequence in ("<Control-Shift-B>", "<Control-Shift-b>"):
            self.bind(sequence, lambda e: (self._backup_now(), "break")[1])
        for sequence in ("<Control-Shift-R>", "<Control-Shift-r>"):
            self.bind(sequence, lambda e: (self._restore_backup(), "break")[1])
        for sequence in ("<Control-Shift-I>", "<Control-Shift-i>"):
            self.bind(sequence, lambda e: (self._import_data(), "break")[1])
        self.bind("<Control-o>", lambda e: (self._open_patient_file(), "break")[1])
        self.bind("<Control-t>", lambda e: (self._toggle_theme(), "break")[1])
        self.bind("<Control-d>", lambda e: (self._show_view("diagnostics"), "break")[1])
        self.bind("<Control-q>", lambda e: (self._on_app_close(), "break")[1])
        self.bind("<F1>", lambda e: (self._show_shortcuts(), "break")[1])
        # Zoom: Ctrl+= / Ctrl+- / Ctrl+0.
        for sequence in ("<Control-equal>", "<Control-plus>", "<Control-KP_Add>"):
            self.bind(sequence, lambda e: (self._zoom(1), "break")[1])
        for sequence in ("<Control-minus>", "<Control-KP_Subtract>"):
            self.bind(sequence, lambda e: (self._zoom(-1), "break")[1])
        self.bind("<Control-0>", lambda e: (self._zoom_reset(), "break")[1])
        self.bind("<Escape>", self._handle_escape)

    def _apply_window_icon(self):
        """Give the window a taskbar icon and a stable Windows app identity.

        Every step is best-effort: a missing asset or a Tcl build without
        ``iconphoto`` support must never stop the app from starting.
        """
        if os.name == "nt":
            try:
                import ctypes

                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MediDashboard.Pro")
            except Exception:
                log.debug_exc(logger)
        for name in ("icon.png", "logo.png"):
            path = os.path.join(_asset_dir(), "assets", name)
            if not os.path.exists(path):
                continue
            try:
                self.iconphoto(True, tk.PhotoImage(file=path))
                return
            except Exception:
                log.debug_exc(logger)
        ico = os.path.join(_asset_dir(), "assets", "icon.ico")
        try:
            if os.path.exists(ico):
                self.iconbitmap(ico)
        except Exception:
            log.debug_exc(logger)

    def _build_status_bar(self) -> None:
        """Build the thin footer that mirrors the patient-file save state."""
        bar = ctk.CTkFrame(
            self,
            fg_color=theme.TOPBAR_BG,
            height=24,
            corner_radius=0,
            border_width=1,
            border_color=theme.BORDER,
        )
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)
        self._status_patient_lbl = ctk.CTkLabel(
            bar, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w"
        )
        self._status_patient_lbl.grid(row=0, column=0, sticky="w", padx=12)
        self._status_state_lbl = ctk.CTkLabel(
            bar, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w"
        )
        self._status_state_lbl.grid(row=0, column=1, sticky="w", padx=12)
        self._status_count_lbl = ctk.CTkLabel(
            bar, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="e"
        )
        self._status_count_lbl.grid(row=0, column=2, sticky="e", padx=12)
        self._status_bar = bar
        self._update_status_bar()

    def _on_patient_status(self, patient_id, state) -> None:
        """Callback passed to patient panels; presentation only, never raises."""
        try:
            self._status_state = state if isinstance(state, str) else ""
            if state == "saved":
                self._status_saved_at = time.strftime("%H:%M")
            elif state in ("open", ""):
                self._status_saved_at = ""
            self._update_status_bar(patient_id)
        except Exception:
            log.debug_exc(logger)

    def _update_status_bar(self, patient_id=None) -> None:
        try:
            bar = getattr(self, "_status_bar", None)
            if bar is None or not bar.winfo_exists():
                return
            if patient_id is None:
                patient_id = self.selected_patient_id
            name = ""
            panel = getattr(self, "patient_panels", {}).get(patient_id)
            if panel is not None:
                name = (getattr(panel, "patient", None) or {}).get("name", "") or ""
            state = getattr(self, "_status_state", "")
            if state == "saved":
                saved_at = getattr(self, "_status_saved_at", "")
                text = lang.t("ui_last_saved", time=saved_at) if saved_at else lang.t("ui_saved")
            elif state == "saving":
                text = lang.t("ui_saving")
            elif state == "unsaved":
                text = lang.t("ui_unsaved")
            else:
                text = ""
            self._status_patient_lbl.configure(
                text=(lang.t("ui_patient_label", name=name) if name else lang.t("ui_no_patient"))
            )
            self._status_state_lbl.configure(text=text)
            self._status_count_lbl.configure(
                text=lang.t("ui_patients_count", n=getattr(self, "_patient_total", 0))
            )
        except Exception:
            log.debug_exc(logger)

    def _on_app_close(self):
        self._closing = True
        try:
            self._save_open_files()
        except Exception:
            log.debug_exc(logger)
        try:
            data = load_settings()
            data["geometry"] = self.geometry()
            save_settings(data)
        except Exception:
            log.debug_exc(logger)
        self.destroy()

    def report_callback_exception(self, exc_type, exc_value, exc_tb):
        """Tkinter sends errors from widget callbacks here.

        Without this override the traceback would only go to stderr, which a
        windowed exe does not have — the user would just see nothing happen.
        """
        if _is_benign_tcl_error(exc_type, exc_value):
            return
        _log_uncaught(exc_type, exc_value, exc_tb)
        if getattr(self, "_closing", False):
            return
        try:
            if self.winfo_exists():
                self._show_status_banner(lang.t("ui_error_banner"))
        except Exception:
            log.debug_exc(logger)
        _show_crash_dialog(exc_value, self)

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
            except Exception:
                log.debug_exc(logger)
        # No inline search box (e.g. a dialog-only layout): fall back to asking.
        try:
            self._search_patients_dialog()
        except Exception:
            log.debug_exc(logger)

    def _handle_escape(self, event=None):
        try:
            entry = getattr(self, "search_entry", None)
            if entry is not None and entry.winfo_exists() and self.focus_get() is entry:
                if entry.get():
                    self._clear_search()
                    return "break"
            self._focus_search()
        except Exception:
            log.debug_exc(logger)
        return "break"

    def _build_menubar(self):
        try:
            self._lang_var.set(lang.get_language())
        except Exception:
            self._lang_var = tk.StringVar(master=self, value=lang.get_language())
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label=lang.t("menu_save_as"), accelerator="Ctrl+Shift+S", command=self._save_as
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=lang.t("ui_backup_now"), accelerator="Ctrl+Shift+B", command=self._backup_now
        )
        file_menu.add_command(
            label=lang.t("ui_restore_backup"),
            accelerator="Ctrl+Shift+R",
            command=self._restore_backup,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=lang.t("ui_import"), accelerator="Ctrl+Shift+I", command=self._import_data
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=lang.t("menu_exit"), accelerator="Ctrl+Q", command=self._on_app_close
        )
        menubar.add_cascade(label=lang.t("menu_file"), menu=file_menu)
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(
            label=lang.t("menu_add_patient"), accelerator="Ctrl+N", command=self._add_patient_db
        )
        edit_menu.add_command(
            label=lang.t("menu_open_patient_file"),
            accelerator="Ctrl+O",
            command=self._open_patient_file,
        )
        edit_menu.add_command(label=lang.t("menu_delete_patient"), command=self._delete_patient_db)
        edit_menu.add_separator()
        edit_menu.add_command(label=lang.t("ui_trash"), command=self._show_trash)
        menubar.add_cascade(label=lang.t("menu_edit"), menu=edit_menu)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(
            label=lang.t("menu_toggle_theme"), accelerator="Ctrl+T", command=self._toggle_theme
        )
        zoom_menu = tk.Menu(view_menu, tearoff=0)
        zoom_menu.add_command(
            label=lang.t("menu_zoom_in"), accelerator="Ctrl++", command=lambda: self._zoom(1)
        )
        zoom_menu.add_command(
            label=lang.t("menu_zoom_out"), accelerator="Ctrl+-", command=lambda: self._zoom(-1)
        )
        zoom_menu.add_command(
            label=lang.t("menu_zoom_reset"), accelerator="Ctrl+0", command=self._zoom_reset
        )
        view_menu.add_cascade(label=lang.t("ui_ui_scale"), menu=zoom_menu)
        lang_submenu = tk.Menu(view_menu, tearoff=0)
        for code, label in LANG_LABELS.items():

            def _pick_language(c: str = code) -> None:
                self._on_language_change("Română" if c == "ro" else "English")

            lang_submenu.add_radiobutton(
                label=label,
                value=code,
                variable=self._lang_var,
                command=_pick_language,
            )
        view_menu.add_cascade(label=lang.t("menu_language"), menu=lang_submenu)
        view_menu.add_separator()
        view_menu.add_command(
            label=lang.t("ui_diagnostics"),
            accelerator="Ctrl+D",
            command=lambda: self._show_view("diagnostics"),
        )
        menubar.add_cascade(label=lang.t("menu_view"), menu=view_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label=lang.t("menu_shortcuts"), accelerator="F1", command=self._show_shortcuts
        )
        help_menu.add_command(label=lang.t("ui_about"), command=self._show_about)
        menubar.add_cascade(label=lang.t("menu_help"), menu=help_menu)
        self.config(menu=menubar)

    def _show_about(self):
        try:
            schema = str(get_database_service().schema_version())
        except Exception:
            schema = "?"
        try:
            if getattr(sys, "frozen", False):
                build = datetime.datetime.fromtimestamp(os.path.getmtime(sys.executable)).strftime(
                    "%d.%m.%Y %H:%M"
                )
            else:
                build = "source"
        except Exception:
            build = "?"
        details = lang.t(
            "about_details",
            build=build,
            schema=schema,
            theme=theme.active(),
            language=lang.get_language().upper(),
            data=_data_dir(),
        )
        messagebox.showinfo(
            lang.t("app_name"),
            lang.t("about_text", app=lang.t("app_name"), version=__version__) + details,
        )

    def _show_shortcuts(self):
        messagebox.showinfo(lang.t("ui_keyboard_shortcuts"), lang.t("ui_shortcuts_body"))

    def _on_language_change(self, choice):
        code = "ro" if choice == "Română" else "en"
        if code == lang.get_language():
            return
        lang.set_language(code)
        save_language(code)
        try:
            self._lang_var.set(code)
        except Exception:
            log.debug_exc(logger)
        # Rebuild behind the veil: header, sidebar, views, menus and the window
        # title all pick up the new language.  The current view, search text and
        # the open patient are restored by _rebuild_ui().
        self.title(lang.t("app_name"))
        self._rebuild_ui()
        self._refresh_settings_dialogs()

    def _build_header_bar(self):
        if theme.active().startswith("medidash"):
            self._build_header_bar_medidash()
            return
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=theme.PADDING, pady=(10, 6))
        bar.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(brand, text="Medi", font=theme.FONT_TITLE, text_color=theme.TEXT).pack(
            side="left"
        )
        ctk.CTkLabel(
            brand, text="Dashboard Pro", font=theme.FONT_TITLE, text_color=theme.ACCENT
        ).pack(side="left")

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            right, text="\u2630", width=40, font=theme.ICON_FONT_SMALL, command=self._toggle_sidebar
        ).pack(side="left", padx=2)
        ctk.CTkButton(right, text=lang.t("ui_theme"), width=70, command=self._toggle_theme).pack(
            side="left", padx=2
        )
        self.lang_menu = ctk.CTkOptionMenu(
            right, values=list(LANG_LABELS.values()), width=95, command=self._on_language_change
        )
        self.lang_menu.set(LANG_LABELS.get(lang.get_language(), "English"))
        self.lang_menu.pack(side="left", padx=2)

    def _build_header_bar_medidash(self):
        bar = ctk.CTkFrame(
            self,
            fg_color=theme.TOPBAR_BG,
            height=theme.TOPBAR_H,
            corner_radius=0,
            border_width=1,
            border_color=theme.BORDER,
        )
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)
        self._header = bar

        # brand
        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w", padx=20)
        try:
            img = ctk.CTkImage(
                light_image=__import__("PIL.Image", fromlist=["Image"]).open(
                    os.path.join(_asset_dir(), "assets", "logo.png")
                ),
                size=(40, 40),
            )
            ctk.CTkLabel(brand, image=img, text="").pack(side="left", padx=(0, 10))
        except Exception:
            ctk.CTkLabel(brand, text="\u2695", font=("Segoe UI", 26), text_color=theme.ACCENT).pack(
                side="left", padx=(0, 10)
            )
        ctk.CTkLabel(
            brand, text="MediDashboard", font=theme.FONT_TITLE, text_color=theme.TEXT
        ).pack(side="left")
        ctk.CTkLabel(brand, text="Pro", font=theme.FONT_TITLE, text_color=theme.ACCENT).pack(
            side="left", padx=(4, 0)
        )

        # right actions
        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.grid(row=0, column=2, sticky="e", padx=20)
        ctk.CTkButton(
            right,
            text="\ue700",
            width=36,
            height=36,
            font=theme.ICON_FONT_SMALL,
            fg_color="transparent",
            text_color=theme.MUTED,
            hover_color=theme.ACCENT_LIGHT,
            command=self._toggle_sidebar,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            right,
            text="\ue721",
            width=36,
            height=36,
            font=theme.ICON_FONT_SMALL,
            fg_color="transparent",
            text_color=theme.MUTED,
            hover_color=theme.ACCENT_LIGHT,
            command=self._focus_search,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            right,
            text="\ue70f",
            width=36,
            height=36,
            font=theme.ICON_FONT_SMALL,
            fg_color="transparent",
            text_color=theme.MUTED,
            hover_color=theme.ACCENT_LIGHT,
            command=self._edit_current_patient,
        ).pack(side="left", padx=2)
        self.lang_menu = ctk.CTkOptionMenu(
            right, values=list(LANG_LABELS.values()), width=90, command=self._on_language_change
        )
        self.lang_menu.set(LANG_LABELS.get(lang.get_language(), "English"))
        self.lang_menu.pack(side="left", padx=6)
        account = ctk.CTkButton(
            right,
            text="\ue77b \ue70d",
            width=60,
            height=36,
            font=theme.ICON_FONT_SMALL,
            fg_color="transparent",
            text_color=theme.MUTED,
            hover_color=theme.ACCENT_LIGHT,
            command=self._show_account_menu,
        )
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
        items = [
            (
                "patients",
                "\U0001f4cb",
                lang.t("tip_patients"),
                lambda: self._show_view("patients"),
                theme.ICON_FONT,
            ),
            (
                "new",
                "\u2795",
                lang.t("tip_new_patient"),
                lambda: self._open_patient_by_id(None),
                theme.ICON_FONT,
            ),
            (
                "saveas",
                "\U0001f4be",
                lang.t("tip_save_as"),
                lambda: self._show_view("saveas"),
                theme.ICON_FONT,
            ),
            (
                "backup",
                "\U0001f5c4",
                lang.t("tip_backup"),
                lambda: self._show_view("backup"),
                theme.ICON_FONT,
            ),
            (
                "trash",
                "\U0001f5d1",
                lang.t("tip_trash"),
                lambda: self._show_view("trash"),
                theme.ICON_FONT,
            ),
            (
                "calendar",
                "\U0001f4c5",
                lang.t("tip_calendar"),
                lambda: self._show_view("calendar"),
                theme.ICON_FONT,
            ),
            (
                "settings",
                "\u2699",
                lang.t("tip_settings"),
                lambda: self._show_view("settings"),
                theme.ICON_FONT,
            ),
        ]
        for key, glyph, tip, cmd, font in items:
            btn = ctk.CTkButton(
                side,
                text=glyph,
                width=44,
                height=44,
                corner_radius=12,
                fg_color="transparent",
                text_color=theme.TEXT,
                hover_color=theme.SIDEBAR_ACTIVE,
                font=font,
                command=cmd,
                border_width=2,
                border_color=theme.BORDER,
            )
            btn.pack(pady=4)
            self._nav_buttons[key] = btn
            attach_tooltip(btn, tip)
        self._set_nav_active("patients")

    def _build_sidebar_medidash(self):
        side = ctk.CTkFrame(
            self, width=theme.RAIL_W, fg_color=theme.RAIL_BG, corner_radius=0, border_width=0
        )
        side.grid(row=1, column=0, sticky="nsw")
        side.grid_propagate(False)
        self._sidebar = side

        self._nav_buttons = {}
        items = [
            ("patients", "\ue716", lang.t("tip_patients"), lambda: self._show_view("patients")),
            (
                "new",
                "\ue710",
                lang.t("tip_new_patient"),
                lambda: self._open_patient_by_id(None),
            ),
            ("saveas", "\ue8a5", lang.t("tip_save_as"), lambda: self._show_view("saveas")),
            ("backup", "\ue753", lang.t("tip_backup"), lambda: self._show_view("backup")),
            ("trash", "\ue74d", lang.t("tip_trash"), lambda: self._show_view("trash")),
            ("calendar", "\ue787", lang.t("tip_calendar"), lambda: self._show_view("calendar")),
        ]
        for key, glyph, tip, cmd in items:
            btn = ctk.CTkButton(
                side,
                text=glyph,
                width=40,
                height=40,
                corner_radius=theme.BTN_RADIUS,
                fg_color="transparent",
                text_color=theme.MUTED,
                hover_color=theme.ACCENT_LIGHT,
                font=theme.ICON_FONT,
                command=cmd,
            )
            btn.pack(pady=6, padx=12)
            self._nav_buttons[key] = btn
            attach_tooltip(btn, tip)
        # settings pinned to bottom
        btn = ctk.CTkButton(
            side,
            text="\ue713",
            width=40,
            height=40,
            corner_radius=theme.BTN_RADIUS,
            fg_color="transparent",
            text_color=theme.MUTED,
            hover_color=theme.ACCENT_LIGHT,
            font=theme.ICON_FONT,
            command=lambda: self._show_view("settings"),
        )
        btn.pack(side="bottom", pady=16, padx=12)
        self._nav_buttons["settings"] = btn
        attach_tooltip(btn, lang.t("tip_settings"))
        self._set_nav_active("patients")

    def _set_nav_active(self, key):
        if theme.active().startswith("medidash"):
            for k, b in getattr(self, "_nav_buttons", {}).items():
                if k == key:
                    b.configure(fg_color=theme.ACCENT, text_color=theme.ON_ACCENT)
                else:
                    b.configure(fg_color="transparent", text_color=theme.MUTED)
            return
        for k, b in getattr(self, "_nav_buttons", {}).items():
            b.configure(fg_color=theme.SIDEBAR_ACTIVE if k == key else "transparent")

    def _toggle_sidebar(self):
        if getattr(self, "_sidebar_visible", True):
            try:
                self._sidebar.grid_remove()
            except Exception:
                log.debug_exc(logger)
            self._sidebar_visible = False
        else:
            try:
                self._sidebar.grid()
            except Exception:
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
        except Exception:
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

        self.overview_panel = ctk.CTkFrame(
            content,
            fg_color=theme.PANEL,
            corner_radius=theme.PANEL_RADIUS,
            border_width=1,
            border_color=theme.BORDER,
        )
        self.overview_panel.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        self.overview_panel.grid_propagate(False)
        self.overview_panel.configure(width=340)
        self._build_overview(self.overview_panel)

        self.file_host = ctk.CTkFrame(
            content,
            fg_color=theme.PANEL,
            corner_radius=theme.PANEL_RADIUS,
            border_width=1,
            border_color=theme.BORDER,
        )
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

        self.overview_title = ctk.CTkLabel(
            parent, text=lang.t("ui_patient_overview"), font=theme.FONT_TITLE, text_color=theme.TEXT
        )
        self.overview_title.grid(
            row=0, column=0, sticky="w", padx=theme.PADDING, pady=(theme.PADDING, 2)
        )

        self.overview_content = ctk.CTkFrame(parent, fg_color="transparent")
        self.overview_content.grid(
            row=1, column=0, sticky="nsew", padx=theme.PADDING, pady=(0, theme.PADDING)
        )
        self.overview_content.grid_columnconfigure(0, weight=1)
        self.overview_content.grid_rowconfigure(0, weight=0)

        self._show_view("patients")

    def _build_overview_medidash(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        parent.configure(fg_color=theme.PANEL)

        self.overview_title = ctk.CTkLabel(
            parent, text=lang.t("ui_patient_overview"), font=theme.FONT_TITLE, text_color=theme.TEXT
        )
        self.overview_title.grid(
            row=0, column=0, sticky="w", padx=theme.PANE_PAD, pady=(theme.PANE_PAD, 2)
        )

        self.overview_content = ctk.CTkFrame(parent, fg_color="transparent")
        self.overview_content.grid(
            row=1, column=0, sticky="nsew", padx=theme.PANE_PAD, pady=(0, theme.PANE_PAD)
        )
        self.overview_content.grid_columnconfigure(0, weight=1)
        self.overview_content.grid_rowconfigure(0, weight=0)

        self._show_view("patients")

    def _show_view(self, view):
        job = getattr(self, "_search_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                log.debug_exc(logger)
            self._search_job = None
        try:
            se = getattr(self, "search_entry", None)
            if se is not None and se.winfo_exists():
                self._search_text = se.get()
            if isinstance(getattr(self, "search_scope", None), str):
                self._search_scope_text = self.search_scope
        except Exception:
            log.debug_exc(logger)
        content = getattr(self, "overview_content", None)
        if content is None:
            return
        # Cover the pane while its children are swapped so the rebuild never
        # shows as a blank flash.  The veil is a sibling of the pane, so it
        # survives the child destruction below.
        veil = self._veil(host=getattr(content, "master", self), target=content, colour=theme.PANEL)
        try:
            for w in content.winfo_children():
                try:
                    w.destroy()
                except Exception:
                    pass
            # reset any row/column weights left over from the previous view
            for i in range(6):
                try:
                    content.grid_rowconfigure(i, weight=0)
                    content.grid_columnconfigure(i, weight=0 if i else 1)
                except Exception:
                    log.debug_exc(logger)
            self._current_view = view
            self._maybe_check_integrity()
            titles = {
                "patients": lang.t("ui_patient_overview"),
                "trash": lang.t("ui_trash"),
                "settings": lang.t("ui_settings"),
                "saveas": lang.t("ui_save_as"),
                "backup": lang.t("view_backup_restore"),
                "new": lang.t("ui_new_patient"),
                "calendar": lang.t("ui_calendar"),
                "diagnostics": lang.t("ui_diagnostics"),
            }
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
            elif view == "diagnostics":
                self._view_diagnostics()
        finally:
            try:
                self.update_idletasks()
            except Exception:
                log.debug_exc(logger)
            if veil is not None:
                try:
                    veil.destroy()
                except Exception:
                    log.debug_exc(logger)

    def _build_search_controls(self, parent):
        """Build the inline search row shared by both dashboard layouts."""
        self.search_scope_menu = ctk.CTkOptionMenu(
            parent,
            values=[lang.t("search_scope_name"), lang.t("search_scope_everything")],
            width=95,
            command=self._on_search_scope_change,
        )
        saved_scope = getattr(self, "_search_scope_text", "everything")
        self.search_scope_menu.set(
            lang.t("search_scope_name")
            if saved_scope == "name"
            else lang.t("search_scope_everything")
        )
        self.search_scope_menu.pack(side="left", padx=(0, 6))
        self.search_scope = saved_scope
        self.search_entry = ctk.CTkEntry(parent, placeholder_text=lang.t("ui_search_patients"))
        self.search_entry.pack(side="left", fill="x", expand=True)
        if getattr(self, "_search_text", ""):
            self.search_entry.insert(0, self._search_text)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Down>", lambda e: (self._navigate_patient(1), "break")[1])
        self.search_entry.bind("<Up>", lambda e: (self._navigate_patient(-1), "break")[1])
        self.search_entry.bind(
            "<Return>", lambda e: (self._navigate_patient(1, open_first=True), "break")[1]
        )
        self.search_entry.bind("<Escape>", lambda e: (self._clear_search(), "break")[1])
        clear_btn = ctk.CTkButton(parent, text="\u00d7", width=26, command=self._clear_search)
        clear_btn.pack(side="left", padx=2)
        attach_tooltip(clear_btn, lang.t("tip_clear_search"))
        self.sort_btn = ctk.CTkButton(parent, text="\u21c5", width=30, command=self._show_sort_menu)
        self.sort_btn.pack(side="left", padx=(2, 0))
        attach_tooltip(self.sort_btn, lang.t("tip_sort"))
        return self.search_entry

    def _view_patients(self):
        f = self.overview_content
        medidash = theme.active().startswith("medidash")
        if medidash:
            f.grid_rowconfigure(2, weight=1)
            search_frame = ctk.CTkFrame(
                f,
                fg_color=theme.INPUT_BG,
                corner_radius=9,
                border_width=1,
                border_color=theme.BORDER,
            )
            search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))
            search_frame.grid_columnconfigure(1, weight=1)
            self._build_search_controls(search_frame)

            self.count_label = ctk.CTkLabel(
                f, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w"
            )
            self.count_label.grid(row=1, column=0, sticky="ew", pady=(0, 2))

            self.card_list = ctk.CTkScrollableFrame(f, fg_color="transparent")
            self.card_list.grid(row=2, column=0, sticky="nsew", pady=(0, 2))
            self.card_list.grid_columnconfigure(0, weight=1)
            utils._patch_scrollable(self.card_list)

            ctk.CTkButton(
                f,
                text=lang.t("ui_new_patient"),
                height=32,
                fg_color=theme.ACCENT,
                hover_color=theme.ACCENT_DARK,
                font=theme.FONT_BOLD,
                command=lambda: self._open_patient_by_id(None),
            ).grid(row=3, column=0, sticky="ew", pady=(2, 0))
            self.refresh_patients_db()
            return

        f.grid_rowconfigure(2, weight=1)
        search_frame = ctk.CTkFrame(
            f, fg_color=theme.INPUT_BG, corner_radius=9, border_width=1, border_color=theme.BORDER
        )
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        search_frame.grid_columnconfigure(1, weight=1)
        self._build_search_controls(search_frame)

        self.count_label = ctk.CTkLabel(
            f, text="", font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w"
        )
        self.count_label.grid(row=1, column=0, sticky="ew", pady=(0, 2))

        self.card_list = ctk.CTkScrollableFrame(f, fg_color="transparent")
        self.card_list.grid(row=2, column=0, sticky="nsew", pady=(0, 2))
        self.card_list.grid_columnconfigure(0, weight=1)
        utils._patch_scrollable(self.card_list)

        ctk.CTkButton(
            f,
            text=lang.t("ui_new_patient"),
            height=32,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_DARK,
            font=theme.FONT_BOLD,
            command=lambda: self._open_patient_by_id(None),
        ).grid(row=3, column=0, sticky="ew", pady=(2, 0))
        self.refresh_patients_db()

    def _on_search_key(self, event=None):
        """Debounce the search so typing does not rebuild the whole list per key."""
        try:
            if getattr(self, "_search_job", None):
                self.after_cancel(self._search_job)
        except Exception:
            log.debug_exc(logger)
        try:
            self._search_job = self.after(
                150,
                lambda: None if getattr(self, "_rebuilding", False) else self.refresh_patients_db(),
            )
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
        rows = get_patient_service().list_deleted()
        for r in rows:
            tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(r.get("name", ""), r.get("localitate", ""), r.get("deleted_at", "")),
            )
        btns = ctk.CTkFrame(f, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        def _restore():
            sel = tree.selection()
            if not sel:
                return
            try:
                get_patient_service().restore_patient(int(sel[0]))
                tree.delete(sel[0])
                self.refresh_patients_db()
            except Exception as e:
                report_error(str(e))

        def _restore_all():
            for iid in list(tree.get_children()):
                try:
                    get_patient_service().restore_patient(int(iid))
                    tree.delete(iid)
                except Exception as e:
                    report_error(str(e))
            self.refresh_patients_db()

        def _purge():
            sel = tree.selection()
            if not sel or not messagebox.askyesno(lang.t("app_name"), lang.t("confirm_purge")):
                return
            get_backup_service().pre_operation("purge")
            get_patient_service().purge_deleted([int(sel[0])])
            tree.delete(sel[0])

        def _empty():
            if not messagebox.askyesno(lang.t("app_name"), lang.t("confirm_empty_trash")):
                return
            get_backup_service().pre_operation("purge")
            get_patient_service().empty_deleted()
            for iid in list(tree.get_children()):
                tree.delete(iid)

        ctk.CTkButton(btns, text=lang.t("ui_restore"), width=80, command=_restore).pack(
            side="left", padx=2
        )
        ctk.CTkButton(btns, text=lang.t("ui_restore_all"), width=90, command=_restore_all).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            btns, text=lang.t("ui_purge"), width=70, fg_color=theme.DANGER, command=_purge
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btns,
            text=lang.t("ui_empty_trash"),
            width=70,
            fg_color=theme.DANGER,
            command=_empty,
        ).pack(side="left", padx=2)

    def _view_settings(self):
        f = self.overview_content
        f.grid_rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(f, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        utils._patch_scrollable(scroll)
        ctk.CTkLabel(
            scroll, text=lang.t("ui_language"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).pack(anchor="w", pady=(0, 2))
        lm = ctk.CTkOptionMenu(
            scroll, values=list(LANG_LABELS.values()), width=200, command=self._on_language_change
        )
        lm.set(LANG_LABELS.get(lang.get_language(), "English"))
        lm.pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(
            scroll, text=lang.t("ui_ui_scale"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).pack(anchor="w", pady=(8, 2))
        sf = ctk.CTkFrame(scroll, fg_color="transparent")
        sf.pack(anchor="w", pady=(0, 10))
        current_scale = self.current_ui_scale()
        for pct in (100, 125, 150):
            _option_button(
                sf,
                str(pct) + "%",
                abs(current_scale - pct / 100.0) < 0.01,
                lambda p=pct: self._set_ui_scale(p / 100.0),
                width=70,
            ).pack(side="left", padx=2)

        ctk.CTkLabel(
            scroll, text=lang.t("ui_theme_label"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).pack(anchor="w", pady=(0, 2))
        tf = ctk.CTkFrame(scroll, fg_color="transparent")
        tf.pack(anchor="w", pady=(0, 10))
        mode = theme.appearance()
        _option_button(
            tf,
            lang.t("ui_light"),
            mode != "Dark",
            lambda: self._apply_appearance("Light"),
        ).pack(side="left", padx=2)
        _option_button(
            tf,
            lang.t("ui_dark"),
            mode == "Dark",
            lambda: self._apply_appearance("Dark"),
        ).pack(side="left", padx=2)
        ctk.CTkLabel(
            scroll, text=lang.t("ui_interface_theme"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).pack(anchor="w", pady=(8, 2))
        itf = ctk.CTkFrame(scroll, fg_color="transparent")
        itf.pack(anchor="w", pady=(0, 10))
        base = theme.base()
        _option_button(
            itf,
            lang.t("ui_theme_classic"),
            base == "classic",
            lambda: self.after(50, lambda: self._apply_ui_theme("classic")),
        ).pack(side="left", padx=2)
        _option_button(
            itf,
            lang.t("ui_theme_medidash"),
            base == "medidash",
            lambda: self.after(50, lambda: self._apply_ui_theme("medidash")),
            width=120,
        ).pack(side="left", padx=2)
        ctk.CTkLabel(
            scroll, text=lang.t("ui_data"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).pack(anchor="w", pady=(8, 2))
        df = ctk.CTkFrame(scroll, fg_color="transparent")
        df.pack(anchor="w", pady=(0, 10))
        ctk.CTkButton(df, text=lang.t("ui_backup_now"), width=110, command=self._backup_now).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            df, text=lang.t("ui_restore_backup"), width=110, command=self._restore_backup
        ).pack(side="left", padx=2)
        ctk.CTkButton(df, text=lang.t("ui_import"), width=110, command=self._import_data).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            scroll,
            text=lang.t("ui_open_trash"),
            width=200,
            command=lambda: self._show_view("trash"),
        ).pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------------
    # Diagnostics: recent errors + health checks (read-only)
    # ------------------------------------------------------------------
    def _view_diagnostics(self):
        f = self.overview_content
        f.grid_rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(f, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        utils._patch_scrollable(scroll)

        head = ctk.CTkFrame(scroll, fg_color="transparent")
        head.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            head, text=lang.t("ui_recent_errors"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).pack(side="left")
        ctk.CTkButton(
            head,
            text=lang.t("ui_refresh"),
            width=70,
            command=lambda: self._show_view("diagnostics"),
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            head, text=lang.t("ui_clear_errors"), width=70, command=self._clear_recent_errors
        ).pack(side="right", padx=2)

        errors = log.recent_errors()
        if not errors:
            ctk.CTkLabel(
                scroll,
                text=lang.t("ui_no_errors"),
                font=theme.FONT_SMALL,
                text_color=theme.MUTED,
                anchor="w",
            ).pack(fill="x", pady=4)
        else:
            for entry in reversed(errors):
                self._build_error_card(scroll, entry)

        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x", pady=(8, 4))
        ctk.CTkButton(
            actions, text=lang.t("ui_copy_errors"), width=130, command=self._copy_recent_errors
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            actions, text=lang.t("ui_open_log"), width=130, command=self._open_log_file
        ).pack(side="left")

        self._build_health_card(scroll)
        self._build_startup_card(scroll)

    def _build_error_card(self, parent, entry):
        """One captured error: time, level, message and its traceback."""
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.PANEL,
            corner_radius=6,
            border_width=1,
            border_color=getattr(theme, "BORDER", theme.MUTED),
        )
        card.pack(fill="x", pady=3)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 0))
        ctk.CTkLabel(top, text=entry["time"], font=theme.FONT_SMALL, text_color=theme.MUTED).pack(
            side="left"
        )
        colour = theme.DANGER if entry["level"] in ("ERROR", "CRITICAL") else theme.ACCENT
        ctk.CTkLabel(top, text=entry["level"], font=theme.FONT_SMALL, text_color=colour).pack(
            side="left", padx=6
        )

        message = entry["message"].strip() or lang.t("ui_no_message")
        if len(message) > 160:
            message = message[:157] + "..."
        ctk.CTkLabel(
            card,
            text=message,
            font=theme.FONT_SMALL,
            text_color=theme.TEXT,
            anchor="w",
            justify="left",
            wraplength=265,
        ).pack(fill="x", padx=8, pady=(2, 4))

        trace_text = entry.get("traceback", "").strip()
        if not trace_text:
            return
        box = ctk.CTkTextbox(
            card,
            height=120,
            font=("Consolas", 9),
            fg_color="transparent",
            border_width=0,
            wrap="word",
        )
        box.pack(fill="x", padx=8, pady=(0, 6))
        box.insert("1.0", trace_text)
        box.configure(state="disabled")

    def _build_health_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.PANEL,
            corner_radius=6,
            border_width=1,
            border_color=getattr(theme, "BORDER", theme.MUTED),
        )
        card.pack(fill="x", pady=(10, 4))
        ctk.CTkLabel(
            card, text=lang.t("ui_health_check"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).pack(anchor="w", padx=8, pady=(8, 4))
        for label, value in self._health_rows():
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)
            ctk.CTkLabel(
                row, text=label, font=theme.FONT_SMALL, text_color=theme.MUTED, anchor="w"
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=value, font=theme.FONT_SMALL, text_color=theme.TEXT, anchor="e"
            ).pack(side="right")
        ctk.CTkLabel(
            card,
            text=lang.t("ui_log_file") + ": " + self._log_path(),
            font=theme.FONT_SMALL,
            text_color=theme.MUTED,
            anchor="w",
            wraplength=265,
        ).pack(fill="x", padx=8, pady=(6, 8))

    def _maybe_check_integrity(self):
        """Periodically verify DB integrity (throttled) and warn on failure."""
        now = time.monotonic()
        last = getattr(self, "_integrity_check_at", 0.0)
        if now - last < 60.0:
            return
        self._integrity_check_at = now
        try:
            ok = get_database_service().check_integrity()
            self._integrity_ok = ok
            if not ok and not getattr(self, "_closing", False):
                logger.warning("periodic integrity check failed")
                try:
                    if self.winfo_exists():
                        self._show_status_banner(lang.t("ui_integrity_failed"))
                except Exception:
                    log.debug_exc(logger)
        except Exception:
            log.debug_exc(logger)
            self._integrity_ok = False

    def _run_startup_checks(self):
        """Run once at launch; results are shown in the Diagnostics view."""
        return run_startup_checks()

    def _build_startup_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.PANEL,
            corner_radius=6,
            border_width=1,
            border_color=getattr(theme, "BORDER", theme.MUTED),
        )
        card.pack(fill="x", pady=(10, 4))
        ctk.CTkLabel(
            card, text=lang.t("ui_startup_checks"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).pack(anchor="w", padx=8, pady=(8, 4))
        check_names = {
            "Database integrity": lang.t("check_db_integrity"),
            "Schema version": lang.t("check_schema_version"),
            "Patients loaded": lang.t("check_patients_loaded"),
            "Settings": lang.t("check_settings"),
            "App assets": lang.t("check_assets"),
            "Backup folder": lang.t("check_backup_folder"),
            "Free disk": lang.t("check_disk_free"),
        }
        for name, ok, detail in getattr(self, "_startup_checks", []):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)
            ctk.CTkLabel(
                row,
                text=check_names.get(name, name),
                font=theme.FONT_SMALL,
                text_color=theme.MUTED,
                anchor="w",
            ).pack(side="left")
            colour = theme.ACCENT if ok else theme.DANGER
            ctk.CTkLabel(
                row, text=detail, font=theme.FONT_SMALL, text_color=colour, anchor="e"
            ).pack(side="right")
        if not getattr(self, "_startup_checks", None):
            ctk.CTkLabel(
                card,
                text=lang.t("ui_not_run"),
                font=theme.FONT_SMALL,
                text_color=theme.MUTED,
                anchor="w",
            ).pack(fill="x", padx=8, pady=(0, 8))

    def _health_rows(self):
        """Read-only checks; each one is guarded so the view never crashes."""
        rows = []
        try:
            ok = get_database_service().check_integrity()
            rows.append((lang.t("ui_db_integrity"), lang.t("ui_ok") if ok else lang.t("ui_failed")))
        except Exception:
            log.debug_exc(logger)
            rows.append((lang.t("ui_db_integrity"), lang.t("ui_failed")))
        try:
            rows.append((lang.t("ui_patients"), str(len(get_patient_service().list_patients()))))
        except Exception:
            log.debug_exc(logger)
        try:
            rows.append((lang.t("ui_appointments"), str(len(get_appointment_service().list()))))
        except Exception:
            log.debug_exc(logger)
        try:
            folder = os.path.join(_data_dir(), "backup")
            backups = glob.glob(os.path.join(folder, "*.db"))
            if backups:
                latest = max(backups, key=os.path.getmtime)
                stamp = datetime.datetime.fromtimestamp(os.path.getmtime(latest)).strftime(
                    "%d.%m.%Y %H:%M"
                )
                rows.append((lang.t("ui_last_backup"), stamp))
            else:
                rows.append((lang.t("ui_last_backup"), lang.t("ui_none")))
        except Exception:
            log.debug_exc(logger)
        try:
            free_gb = shutil.disk_usage(_data_dir()).free / (1024.0**3)
            rows.append((lang.t("ui_disk_free"), f"{free_gb:.1f} GB"))
        except Exception:
            log.debug_exc(logger)
        return rows

    def _log_path(self):
        return os.path.join(_data_dir(), "app.log")

    def _clear_recent_errors(self):
        log.clear_errors()
        self._show_view("diagnostics")

    def _copy_recent_errors(self):
        errors = log.recent_errors()
        if not errors:
            return
        lines = []
        for entry in reversed(errors):
            lines.append(
                "{} {} {}: {}".format(
                    entry["time"], entry["level"], entry["logger"], entry["message"]
                )
            )
            if entry.get("traceback"):
                lines.append(entry["traceback"])
        try:
            self.clipboard_clear()
            self.clipboard_append("\n".join(lines))
            self._show_status_banner(lang.t("ui_copied"))
        except Exception:
            log.debug_exc(logger)

    def _open_log_file(self):
        path = self._log_path()
        if not os.path.exists(path):
            messagebox.showinfo(lang.t("app_name"), lang.t("ui_no_log_file"))
            return
        try:
            os.startfile(path)
        except Exception as e:
            log.debug_exc(logger)
            report_error(str(e))

    def _view_saveas(self):
        f = self.overview_content
        f.grid_rowconfigure(0, weight=1)
        inner = ctk.CTkFrame(f, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(
            inner, text=lang.t("ui_choose_format"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).pack(anchor="w", pady=(0, 6))
        self._saveas_fmt = tk.StringVar(master=self, value="excel")
        fmt = self._saveas_fmt
        for val, lbl in [
            ("excel", lang.t("ui_export_excel")),
            ("csv", lang.t("ui_export_csv")),
            ("pdf", lang.t("ui_export_pdf")),
            ("word", lang.t("ui_export_word")),
        ]:
            ctk.CTkRadioButton(inner, text=lbl, variable=fmt, value=val).pack(anchor="w", pady=2)

        def _go():
            v = fmt.get()
            if v == "excel":
                self._export_excel()
            elif v == "csv":
                self._export_csv()
            elif v == "pdf":
                self._export_pdf()
            elif v == "word":
                self._export_word()

        ctk.CTkButton(
            inner, text=lang.t("ui_export"), width=120, fg_color=theme.ACCENT, command=_go
        ).pack(anchor="w", pady=(10, 0))

    def _view_backup(self):
        f = self.overview_content
        f.grid_rowconfigure(0, weight=1)
        inner = ctk.CTkFrame(f, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew")
        ctk.CTkButton(
            inner, text=lang.t("ui_backup_now"), width=140, command=self._backup_now
        ).pack(anchor="w", pady=4)
        ctk.CTkButton(
            inner, text=lang.t("ui_restore_backup"), width=140, command=self._restore_backup
        ).pack(anchor="w", pady=4)

    def _view_calendar(self):
        f = self.overview_content
        f.grid_rowconfigure(1, weight=0)
        # month navigation
        nav = ctk.CTkFrame(f, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._cal_year = getattr(self, "_cal_year", datetime.date.today().year)
        self._cal_month = getattr(self, "_cal_month", datetime.date.today().month)

        def _render():
            for w in grid.winfo_children():
                w.destroy()
            import calendar as _cal

            title_lbl.configure(
                text="%s %d" % (lang.t("cal_month_%d" % self._cal_month), self._cal_year)
            )
            # weekday headers
            for i in range(7):
                wd = lang.t("cal_weekday_%d" % (i + 1))
                ctk.CTkLabel(grid, text=wd, font=theme.FONT_BOLD, text_color=theme.MUTED).grid(
                    row=0, column=i, padx=2, pady=2
                )
            cal = _cal.Calendar(firstweekday=0)
            weeks = cal.monthdayscalendar(self._cal_year, self._cal_month)
            apps = get_appointment_service().list()
            by_day: dict[int, list[dict[str, object]]] = {}
            for a in apps:
                try:
                    d = (
                        datetime.datetime.strptime(a["datetime"], "%d.%m.%Y %H:%M")
                        if " " in a["datetime"]
                        else datetime.datetime.strptime(a["datetime"], "%d.%m.%Y")
                    )
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
                    btn = ctk.CTkButton(
                        grid,
                        text=txt,
                        width=44,
                        height=32,
                        fg_color=theme.SELECTED if day in by_day else "transparent",
                        text_color=theme.TEXT,
                        hover_color=theme.ACCENT_LIGHT,
                        command=lambda d=day: self._show_day_appointments(d),
                    )
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
        grid = ctk.CTkFrame(f, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="nsew", pady=4)
        _render()

        # --- new-appointment form directly under the calendar
        self._cal_selected_day = (
            getattr(self, "_cal_selected_day", None) or datetime.date.today().day
        )
        try:
            import calendar as _cal3

            max_day = _cal3.monthrange(self._cal_year, self._cal_month)[1]
            self._cal_selected_day = min(int(self._cal_selected_day), max_day)
        except Exception:
            log.debug_exc(logger)
        form = ctk.CTkFrame(
            f,
            fg_color=theme.PANEL,
            corner_radius=getattr(theme, "CARD_RADIUS", 8),
            border_width=1,
            border_color=getattr(theme, "BORDER", theme.MUTED),
        )
        form.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        form.grid_columnconfigure(1, weight=1)
        self._cal_form_date = ctk.CTkLabel(
            form, text="", font=theme.FONT_BOLD, text_color=theme.TEXT, anchor="w"
        )
        self._cal_form_date.grid(row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(8, 2))
        self._cal_form_date.configure(
            text="%s \u2013 %02d.%02d.%d"
            % (
                lang.t("ui_new_appointment"),
                self._cal_selected_day,
                self._cal_month,
                self._cal_year,
            )
        )

        ctk.CTkLabel(
            form, text=lang.t("ui_patient") + ":", font=theme.FONT_SMALL, text_color=theme.MUTED
        ).grid(row=1, column=0, sticky="w", padx=8)
        patients = {}
        try:
            for p in get_patient_service().list_patients():
                patients[p["name"]] = p
        except Exception:
            log.debug_exc(logger)
        self._cal_patients = patients
        names = sorted(patients.keys())
        self._cal_pat_var = ctk.StringVar(master=self, value=(names[0] if names else "\u2014"))
        ctk.CTkOptionMenu(
            form, values=names if names else ["\u2014"], variable=self._cal_pat_var, width=170
        ).grid(row=1, column=1, columnspan=3, sticky="w", padx=8, pady=2)

        ctk.CTkLabel(
            form, text=lang.t("ui_time"), font=theme.FONT_SMALL, text_color=theme.MUTED
        ).grid(row=2, column=0, sticky="w", padx=8)
        self._cal_time_var = ctk.StringVar(master=self, value="09:00")
        ctk.CTkEntry(form, textvariable=self._cal_time_var, width=80, justify="center").grid(
            row=2, column=1, sticky="w", padx=8, pady=2
        )
        ctk.CTkLabel(
            form, text=lang.t("ui_duration_min"), font=theme.FONT_SMALL, text_color=theme.MUTED
        ).grid(row=2, column=2, sticky="e")
        self._cal_dur_var = ctk.StringVar(master=self, value="30")
        ctk.CTkEntry(form, textvariable=self._cal_dur_var, width=60, justify="center").grid(
            row=2, column=3, sticky="w", padx=(2, 8), pady=2
        )

        ctk.CTkLabel(
            form, text=lang.t("ui_status") + ":", font=theme.FONT_SMALL, text_color=theme.MUTED
        ).grid(row=3, column=0, sticky="w", padx=8)
        self._cal_status_var = ctk.StringVar(master=self, value="scheduled")
        ctk.CTkOptionMenu(
            form, values=list(SESSION_STATUSES), variable=self._cal_status_var, width=140
        ).grid(row=3, column=1, columnspan=3, sticky="w", padx=8, pady=2)

        ctk.CTkLabel(
            form, text=lang.t("ui_notes") + ":", font=theme.FONT_SMALL, text_color=theme.MUTED
        ).grid(row=4, column=0, sticky="nw", padx=8)
        self._cal_notes_entry = ctk.CTkEntry(form, placeholder_text=lang.t("ui_notes"))
        self._cal_notes_entry.grid(row=4, column=1, columnspan=3, sticky="ew", padx=8, pady=2)

        ctk.CTkButton(
            form,
            text=lang.t("ui_add_appointment"),
            fg_color=theme.ACCENT,
            command=self._cal_add_appointment,
        ).grid(row=5, column=0, columnspan=4, sticky="ew", padx=8, pady=(6, 2))
        self._cal_err = ctk.CTkLabel(
            form, text="", font=theme.FONT_SMALL, text_color=theme.DANGER, anchor="w"
        )
        self._cal_err.grid(row=6, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 8))

    def _cal_add_appointment(self):
        try:
            self._cal_err.configure(text="")
        except Exception:
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
            if hh is None or mm is None or not (0 <= hh < 24 and 0 <= mm < 60):
                self._cal_err.configure(text=lang.t("ui_invalid_time"))
                return
            try:
                dur = max(5, int(self._cal_dur_var.get()))
            except ValueError:
                log.debug_exc(logger)
                dur = 30
            day = getattr(self, "_cal_selected_day", datetime.date.today().day)
            dt = "%02d.%02d.%d %02d:%02d" % (day, self._cal_month, self._cal_year, hh, mm)
            get_appointment_service().add(
                p["id"],
                dt,
                duration_min=dur,
                status=self._cal_status_var.get(),
                notes=self._cal_notes_entry.get().strip(),
            )
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
                    self._cal_form_date.configure(
                        text="{} \u2013 {}".format(lang.t("ui_new_appointment"), date_str)
                    )
            except Exception:
                log.debug_exc(logger)
        # leaving any open patient file: save it first, then swap the preview
        try:
            self._save_open_files()
        except Exception:
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
        ctk.CTkLabel(
            head, text=date_str, font=theme.FONT_TITLE, text_color=theme.TEXT, anchor="w"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(head, text="\u2715", width=30, command=self._show_placeholder).grid(
            row=0, column=1, padx=(8, 0)
        )

        # --- scrollable list of appointment cards
        lst = ctk.CTkScrollableFrame(root, fg_color="transparent")
        lst.grid(row=1, column=0, sticky="nsew", padx=theme.PADDING)
        lst.grid_columnconfigure(0, weight=1)
        try:
            utils._patch_scrollable(lst)
        except Exception:
            log.debug_exc(logger)

        def _render_list():
            for w in lst.winfo_children():
                w.destroy()
            apps = []
            for a in get_appointment_service().list():
                try:
                    d = datetime.datetime.strptime(a["datetime"].split(" ")[0], "%d.%m.%Y")
                except Exception:
                    log.debug_exc(logger)
                    continue
                if d.day == day and d.month == self._cal_month and d.year == self._cal_year:
                    apps.append(a)
            apps.sort(
                key=lambda a: (
                    a["datetime"].split(" ")[1] if " " in a["datetime"] else "99:99",
                    a["id"],
                )
            )
            if not apps:
                ctk.CTkLabel(
                    lst,
                    text=lang.t("ui_no_appointments"),
                    font=theme.FONT_SUB,
                    text_color=theme.MUTED,
                    anchor="w",
                ).grid(row=0, column=0, sticky="w", padx=4, pady=10)
                return
            pmap = {}
            try:
                for p in get_patient_service().list_patients():
                    pmap[p["id"]] = p["name"]
            except Exception:
                log.debug_exc(logger)
            for i, a in enumerate(apps):
                card = ctk.CTkFrame(
                    lst,
                    fg_color=theme.PANEL,
                    corner_radius=6,
                    border_width=1,
                    border_color=getattr(theme, "BORDER", theme.MUTED),
                )
                card.grid(row=i, column=0, sticky="ew", padx=2, pady=3)
                card.grid_columnconfigure(1, weight=1)
                time_str = a["datetime"].split(" ")[1] if " " in a["datetime"] else "--:--"
                ctk.CTkLabel(
                    card,
                    text=time_str,
                    font=theme.FONT_BOLD,
                    text_color=theme.ACCENT,
                    width=60,
                    anchor="w",
                ).grid(row=0, column=0, padx=(10, 4), pady=6)
                name = pmap.get(a["patient_id"], "?")
                ctk.CTkLabel(
                    card, text=name, font=theme.FONT_BODY, text_color=theme.TEXT, anchor="w"
                ).grid(row=0, column=1, sticky="w", padx=2)
                ctk.CTkLabel(
                    card,
                    text=lang.t("ui_minutes", n=a.get("duration_min") or 0),
                    font=theme.FONT_SMALL,
                    text_color=theme.MUTED,
                    width=60,
                ).grid(row=0, column=2, padx=2)
                st_var = ctk.StringVar(master=self, value=a.get("status", "scheduled"))

                def _set_status(v, aid=a["id"]):
                    get_appointment_service().update(aid, status=v)
                    _render_list()
                    self._show_view("calendar")

                ctk.CTkOptionMenu(
                    card,
                    values=list(SESSION_STATUSES),
                    variable=st_var,
                    width=110,
                    command=lambda v, f=_set_status: f(v),
                ).grid(row=0, column=3, padx=4)

                def _del(btn, aid=a["id"]):
                    if btn.cget("text") != "\u2713":
                        btn.configure(text="\u2713", fg_color=theme.DANGER)
                        return
                    get_appointment_service().delete(aid)
                    _render_list()
                    self._show_view("calendar")

                del_btn = ctk.CTkButton(
                    card,
                    text="\u2715",
                    width=30,
                    fg_color="transparent",
                    border_width=1,
                    border_color=getattr(theme, "BORDER", theme.MUTED),
                    text_color=theme.MUTED,
                    hover_color=theme.DANGER_HOVER,
                )
                # wire two-step confirm without popups: first click arms the button
                del_btn.configure(command=lambda b=del_btn: _del(b))
                del_btn.grid(row=0, column=4, padx=(0, 8))

        _render_list()

    def _view_new_patient(self):
        self._open_patient_by_id(None)
        self._show_view("patients")

    def _show_placeholder(self):
        for w in self.file_host.winfo_children():
            w.destroy()
        lbl = ctk.CTkLabel(
            self.file_host,
            text=lang.t("ui_select_patient_file"),
            font=theme.FONT_SUB,
            text_color=theme.MUTED,
        )
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
            patients = get_patient_service().list_patients(
                sort_by=self.sort_by, sort_dir=self.sort_dir
            )
            self._patient_total = len(patients)
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
                diag_text = p.get("diagnostic", "") or ""
                first_line = (
                    utils._strip_inline_formatting(diag_text).split(chr(10))[0] if diag_text else ""
                )
                if scope == "name":
                    haystack = _norm(p.get("name", ""))
                else:
                    haystack = _norm(
                        " ".join(
                            [
                                str(p.get("name", "")),
                                str(p.get("localitate", "")),
                                diag_text,
                                p.get("objective", "") or "",
                                p.get("evaluation", "") or "",
                                p.get("observation", "") or "",
                            ]
                        )
                    )
                if search and search not in haystack:
                    continue
                shown += 1
                self._visible_patient_ids.append(p.get("id"))
                self._build_patient_card(p, first_line, (p.get("id") == self.selected_patient_id))
            if hasattr(self, "count_label"):
                if search:
                    count_text = lang.t("overview_count", n=shown, total=len(patients))
                else:
                    count_text = lang.t("overview_count_all", n=shown)
                try:
                    count_text += "  \u00b7  " + self._sort_label()
                except Exception:
                    log.debug_exc(logger)
                self.count_label.configure(text=count_text)
            if not patients:
                self._show_list_empty(lang.t("empty_no_patients"))
            elif not self._visible_patient_ids:
                self._show_list_empty(lang.t("empty_no_match", q=search_raw.strip()))
            self._update_status_bar()
        except Exception as e:
            report_error(str(e))
        try:
            if (
                "_canvas" in locals()
                and _canvas is not None
                and "_yview" in locals()
                and _yview is not None
            ):
                _canvas.yview_moveto(_yview[0])
        except Exception:
            log.debug_exc(logger)

    def _show_list_empty(self, text):
        try:
            ctk.CTkLabel(
                self.card_list,
                text=text,
                font=theme.FONT_SMALL,
                text_color=theme.MUTED,
                wraplength=280,
                justify="left",
            ).pack(anchor="w", padx=10, pady=12)
        except Exception:
            log.debug_exc(logger)

    def _build_patient_card(self, p, first_line, selected):
        card = ctk.CTkFrame(
            self.card_list,
            fg_color=theme.SELECTED if selected else theme.PANEL,
            corner_radius=theme.CARD_RADIUS,
            border_width=1,
            border_color=theme.BORDER,
        )
        card.pack(fill="x", pady=1)
        card.grid_columnconfigure(1, weight=1)

        av = ctk.CTkLabel(
            card,
            text=_initials(p.get("name", "")),
            width=theme.AVATAR_SIZE,
            height=theme.AVATAR_SIZE,
            corner_radius=theme.AVATAR_SIZE // 2,
            fg_color=theme.ACCENT,
            text_color=theme.ON_ACCENT,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        av.grid(row=0, column=0, rowspan=3, padx=8, pady=1)

        name_lbl = ctk.CTkLabel(
            card, text=p.get("name", ""), font=theme.FONT_BOLD, text_color=theme.TEXT, anchor="w"
        )
        name_lbl.grid(row=0, column=1, sticky="w", pady=(2, 0))

        meta = ctk.CTkLabel(
            card,
            text=p.get("localitate", "") or "\u2014",
            font=theme.FONT_SMALL,
            text_color=theme.CARD_META,
            anchor="w",
        )
        meta.grid(row=1, column=1, sticky="w")

        preview = ctk.CTkLabel(
            card,
            text=(first_line[:50] + ("..." if len(first_line) > 50 else ""))
            or lang.t("ui_no_diagnostic"),
            font=theme.FONT_SMALL,
            text_color=theme.CARD_META,
            anchor="w",
        )
        preview.grid(row=2, column=1, sticky="w", pady=(0, 2))

        open_btn = ctk.CTkButton(
            card,
            text=lang.t("ui_open_file") + " \u203a",
            width=80,
            height=24,
            corner_radius=8,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_DARK,
            font=theme.FONT_SMALL,
            command=lambda pid=p["id"]: self._open_patient_by_id(pid),
        )
        open_btn.grid(row=0, column=2, rowspan=3, padx=10)
        if not selected:
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
        except Exception:
            log.debug_exc(logger)
        card.bind("<Return>", lambda e=None, pid=p["id"]: self._open_patient_by_id(pid))
        card.bind("<space>", lambda e=None, pid=p["id"]: self._open_patient_by_id(pid))
        card.bind("<Down>", lambda e=None: (self._navigate_patient(1), "break")[1])
        card.bind("<Up>", lambda e=None: (self._navigate_patient(-1), "break")[1])
        for w in (card, av, name_lbl, meta, preview):
            w.bind("<Button-1>", lambda e=None, pid=p["id"]: self._open_patient_by_id(pid))
            w.bind("<Button-3>", lambda e=None, pid=p["id"]: self._card_context(e, pid))

        self._card_widgets[p.get("id")] = (card, open_btn)

    def _card_context(self, event, pid):
        if event is None:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label=lang.t("btn_edit_patient"), command=lambda: self._edit_patient_by_id(pid)
        )
        menu.add_command(label=lang.t("ui_delete"), command=lambda: self._delete_by_id(pid))
        menu.add_command(label=lang.t("ui_copy_name"), command=lambda: self._copy_name_by_id(pid))
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
            if messagebox.askyesno(lang.t("app_name"), lang.t("confirm_delete_current")):
                page = self.patient_panels.pop(pid, None)
                if page is not None:
                    try:
                        if page.winfo_exists():
                            page.destroy()
                    except Exception:
                        log.debug_exc(logger)
                svc = get_patient_service()
                deleted_row_id = svc.delete_patient(pid)
                if deleted_row_id is not None:
                    self._last_deleted_row_id = deleted_row_id
                    self._last_deleted_name = None
                    try:
                        for d in svc.list_deleted():
                            if d.get("id") == deleted_row_id:
                                self._last_deleted_name = d.get("name")
                                break
                    except Exception:
                        log.debug_exc(logger)
                if self.selected_patient_id == pid:
                    self.selected_patient_id = None
                    self._show_placeholder()
                self.refresh_patients_db()
                self._show_undo_hint()
        except Exception as e:
            report_error(str(e))

    def _show_status_banner(self, text):
        """Show a short status message at the bottom of the overview panel."""
        try:
            banner = ctk.CTkLabel(
                self.overview_content,
                text=text,
                fg_color=theme.ACCENT,
                text_color=theme.ON_ACCENT,
                corner_radius=6,
                font=theme.FONT_SMALL,
                padx=10,
                pady=4,
            )
            banner.place(relx=0.5, rely=1.0, anchor="s", y=-8)
            banner.lift()
            self.after(
                4000,
                lambda b=banner: (
                    None if getattr(self, "_rebuilding", False) else utils._safe_destroy(b)
                ),
            )
        except Exception:
            log.debug_exc(logger)

    def _show_undo_hint(self):
        """Show a short, non-blocking 'Ctrl+Z to undo' banner after a delete."""
        name = getattr(self, "_last_deleted_name", None) or "patient"
        try:
            hint = ctk.CTkLabel(
                self.overview_content,
                text=lang.t("ui_deleted_patient", name=str(name))
                + " \u00b7 "
                + lang.t("ui_ctrl_z_undo"),
                fg_color=theme.DANGER,
                text_color=theme.ON_ACCENT,
                corner_radius=6,
                font=theme.FONT_SMALL,
                padx=10,
                pady=4,
            )
            hint.place(relx=0.5, rely=1.0, anchor="s", y=-46)
            hint.lift()
            self._undo_hint = hint
            self.after(
                6000,
                lambda: None if getattr(self, "_rebuilding", False) else utils._safe_destroy(hint),
            )
        except Exception:
            log.debug_exc(logger)

    def _handle_ctrl_z(self, event=None):
        w = self.focus_get()
        if isinstance(w, tk.Text):
            try:
                w.event_generate("<<Undo>>")
            except Exception:
                log.debug_exc(logger)
            return "break"
        self._undo_last_delete(event)
        return "break"

    def _handle_ctrl_y(self, event=None):
        w = self.focus_get()
        if isinstance(w, tk.Text):
            try:
                w.event_generate("<<Redo>>")
            except Exception:
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
                except Exception:
                    log.debug_exc(logger)
                self._undo_hint = None
            new_pid = get_patient_service().restore_patient(row_id)
            self._last_deleted_row_id = None
            self._last_deleted_name = None
            self.refresh_patients_db()
            if new_pid is not None:
                self._open_patient_by_id(new_pid)
            messagebox.showinfo(lang.t("app_name"), lang.t("ui_restore_patient"))
        except Exception as e:
            report_error(str(e))
        return "break"

    def _copy_name_by_id(self, pid):
        p = get_patient_service().get_patient(patient_id=pid)
        if p:
            self.clipboard_clear()
            self.clipboard_append(p.get("name", ""))

    def _save_open_files(self):
        """Persist unsaved edits in open patient files before switching away or exiting."""
        for pid, panel in list(getattr(self, "patient_panels", {}).items()):
            try:
                if panel.winfo_exists():
                    panel.save_if_dirty()
            except Exception:
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
        except Exception:
            log.debug_exc(logger)
        for cid, (card, btn) in list(getattr(self, "_card_widgets", {}).items()):
            try:
                if cid == pid:
                    card.configure(fg_color=theme.SELECTED)
                    btn.grid()
                else:
                    card.configure(fg_color=theme.PANEL)
                    btn.grid_remove()
            except Exception:
                log.debug_exc(logger)
        try:
            if _canvas is not None and _yview is not None:

                def _restore_scroll():
                    try:
                        if _canvas.winfo_exists():
                            _canvas.yview_moveto(_yview[0])
                    except Exception:
                        log.debug_exc(logger)

                self.after_idle(_restore_scroll)
        except Exception:
            log.debug_exc(logger)

    def _open_patient_by_id(self, patient_id):
        # warn before discarding an unsaved new patient
        for pid, panel in list(getattr(self, "patient_panels", {}).items()):
            if getattr(panel, "_is_new", False) and getattr(panel, "_dirty", False):
                if not messagebox.askyesno(lang.t("app_name"), lang.t("confirm_discard_new")):
                    return
        if patient_id is None:
            self._save_open_files()
            for w in self.file_host.winfo_children():
                w.destroy()
            self.patient_panels = {}
            panel = PatientFilePanel(
                self.file_host,
                None,
                on_close=self.refresh_patients_db,
                on_status=self._on_patient_status,
                new=True,
            )
            panel.place(relx=0, rely=0, relwidth=1, relheight=1, x=0)
            self.patient_panels[None] = panel
            self.selected_patient_id = None
            self._status_state = ""
            self._status_saved_at = ""
            self._update_status_bar(None)
            return
        self._save_open_files()
        self.selected_patient_id = patient_id
        for w in self.file_host.winfo_children():
            w.destroy()
        self.patient_panels = {}
        panel = PatientFilePanel(
            self.file_host,
            patient_id,
            on_close=self.refresh_patients_db,
            on_status=self._on_patient_status,
        )
        # show immediately (no slide-in clip)
        panel.place(relx=0, rely=0, relwidth=1, relheight=1, x=0)
        self.patient_panels[patient_id] = panel
        self._set_selected_card(patient_id)
        self._status_state = ""
        self._status_saved_at = ""
        self._update_status_bar(patient_id)

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
            from dialogs.input_dialog import ask_string

            term = ask_string(
                self,
                lang.t("search_title"),
                lang.t("search_prompt"),
                initialvalue=getattr(self, "_search_text", ""),
            )
        except Exception:
            term = None
        if term is None:
            return
        self._search_text = term.strip()
        self.refresh_patients_db()

    def _clear_search(self):
        try:
            entry = getattr(self, "search_entry", None)
            if entry is not None and entry.winfo_exists():
                entry.delete(0, "end")
        except Exception:
            log.debug_exc(logger)
        self._search_text = ""
        self.refresh_patients_db()

    def _on_search_scope_change(self, value: str) -> None:
        self.search_scope = "name" if value == lang.t("search_scope_name") else "everything"
        self.refresh_patients_db()

    def current_ui_scale(self) -> float:
        """User-selected interface scale (1.0, 1.25 or 1.5)."""
        return float(getattr(self, "_ui_scale", 1.0))

    def _zoom_steps(self):
        return (1.0, 1.25, 1.5)

    def _zoom(self, direction):
        steps = self._zoom_steps()
        current = self.current_ui_scale()
        if current not in steps:
            index = 0
        else:
            index = steps.index(current)
        index = max(0, min(len(steps) - 1, index + direction))
        if steps[index] != current:
            self._set_ui_scale(steps[index])

    def _zoom_reset(self):
        if self.current_ui_scale() != 1.0:
            self._set_ui_scale(1.0)

    def _set_ui_scale(self, scale):
        try:
            scale = float(scale)
        except (TypeError, ValueError):
            return
        if scale not in self._zoom_steps():
            return
        self._ui_scale = scale
        try:
            ctk.set_widget_scaling(scale)
            ctk.set_window_scaling(scale)
        except Exception:
            log.debug_exc(logger)
        try:
            data = load_settings()
            data["ui_scale"] = scale
            save_settings(data)
        except Exception:
            log.debug_exc(logger)
        # CustomTkinter rescales live, but rebuilding behind the veil keeps the
        # fonts, geometry and ttk styling of every view consistent.
        self._rebuild_ui()
        self._refresh_settings_dialogs()

    def _refresh_settings_dialogs(self):
        """Ask any open settings windows to re-render their labels."""
        for dialog in list(getattr(self, "_settings_dialogs", [])):
            try:
                if dialog.winfo_exists():
                    dialog.refresh_language()
            except Exception:
                log.debug_exc(logger)

    def _toggle_theme(self):
        cur = ctk.get_appearance_mode()
        self._apply_appearance("Dark" if cur == "Light" else "Light")
        self._refresh_settings_dialogs()

    def _recolour(self, old_palette, old_active=None):
        """Translate palette colours in place; rebuild only as a fallback."""
        if old_active is None:
            old_active = theme.active()
        try:
            changed = recolor.apply(self, old_palette)
        except Exception:
            log.debug_exc(logger)
            changed = 0
        if changed == 0 and theme.active() != old_active:
            # Nothing matched the old palette: a rebuild is safer than leaving
            # the window half-recoloured.
            self._rebuild_ui()
        return changed

    def _veil(self, host=None, target=None, colour=None):
        """Opaque cover drawn while widgets are destroyed and rebuilt.

        Returns the veil so the caller can destroy it once the new widgets are
        laid out.  Best effort: a failure simply means no veil.
        """
        host = host if host is not None else self
        try:
            veil = ctk.CTkFrame(
                host,
                fg_color=colour if colour is not None else theme.BG,
                corner_radius=0,
            )
            if target is not None and target.winfo_exists():
                veil.place(in_=target, relx=0, rely=0, relwidth=1, relheight=1)
            else:
                veil.place(relx=0, rely=0, relwidth=1, relheight=1)
            veil.lift()
            self.update_idletasks()
            return veil
        except Exception:
            log.debug_exc(logger)
            return None

    def _rebuild_ui(self):
        self._rebuilding = True
        veil = self._veil(colour=theme.BG)
        try:
            self._save_open_files()
            self._build_menubar()
            view = getattr(self, "_current_view", "patients")
            pid = self.selected_patient_id
            search_text = getattr(self, "_search_text", "")
            search_scope = getattr(self, "_search_scope_text", "everything")
            # Move focus away before destroying widgets to avoid "bad window path"
            # TclErrors from Tk trying to refocus a destroyed child.
            try:
                self.focus_set()
            except Exception:
                pass
            for w in (
                getattr(self, "_header", None),
                getattr(self, "_sidebar", None),
                getattr(self, "_content", None),
                getattr(self, "_status_bar", None),
            ):
                try:
                    if w is not None and w.winfo_exists():
                        w.destroy()
                except Exception:
                    log.debug_exc(logger)
            self._header = None
            self._sidebar = None
            self._content = None
            self._status_bar = None
            ttk_style.apply(self, scale=self.current_ui_scale())
            self.grid_columnconfigure(0, weight=0)
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(0, weight=0)
            self.grid_rowconfigure(1, weight=1)
            self.grid_rowconfigure(2, weight=0)
            self._build_header_bar()
            self._build_sidebar()
            self._build_content()
            self._build_status_bar()
            self._search_text = search_text
            self._search_scope_text = search_scope
            try:
                self._show_view(view if view else "patients")
            except Exception:
                self._show_view("patients")
            if pid is not None:
                try:
                    self._open_patient_by_id(pid)
                except Exception:
                    log.debug_exc(logger)
            self._sidebar_visible = True
            try:
                self._on_configure_responsive()
            except Exception:
                log.debug_exc(logger)
        finally:
            try:
                self.update_idletasks()
            except Exception:
                log.debug_exc(logger)
            if veil is not None:
                try:
                    veil.destroy()
                except Exception:
                    log.debug_exc(logger)

    def _show_account_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=lang.t("account_language", code=lang.get_language().upper()))
        menu.add_command(label=lang.t("account_toggle_theme"), command=self._toggle_theme)
        menu.add_separator()
        menu.add_command(
            label=lang.t("account_theme", name=lang.t("ui_theme_classic")),
            command=lambda: self._apply_ui_theme("classic"),
        )
        menu.add_command(
            label=lang.t("account_theme", name=lang.t("ui_theme_medidash")),
            command=lambda: self._apply_ui_theme("medidash"),
        )
        menu.add_separator()
        menu.add_command(label=lang.t("menu_shortcuts"), command=self._show_shortcuts)
        menu.add_command(label=lang.t("ui_about"), command=self._show_about)
        try:
            btn = getattr(self, "_account_btn", None)
            x = (
                btn.winfo_rootx()
                if (btn is not None and btn.winfo_exists())
                else self.winfo_rootx()
            )
            y = (
                (btn.winfo_rooty() + btn.winfo_height())
                if (btn is not None and btn.winfo_exists())
                else self.winfo_rooty()
            )
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                log.debug_exc(logger)

    def _apply_appearance(self, mode):
        mode = "Dark" if str(mode).lower().startswith("d") else "Light"
        old_palette = recolor.snapshot()
        old_active = theme.active()
        ctk.set_appearance_mode(mode)
        try:
            theme.set_appearance(mode)
        except Exception:
            log.debug_exc(logger)
        # Light/dark keeps the same layout, so recolour in place instead of
        # destroying and recreating the whole window.
        self._recolour(old_palette, old_active)
        try:
            data = load_settings()
            data["appearance"] = mode
            save_settings(data)
        except Exception:
            log.debug_exc(logger)

    def _apply_ui_theme(self, name):
        if name not in ("classic", "medidash"):
            name = "medidash"
        self._save_open_files()
        try:
            data = load_settings()
            data["ui_theme"] = name
            save_settings(data)
        except Exception:
            log.debug_exc(logger)
        old_palette = recolor.snapshot()
        old_base = theme.base()
        old_active = theme.active()
        theme.set_theme(name)
        if theme.base() == old_base:
            # Same layout, different palette (e.g. classic-dark -> classic).
            self._recolour(old_palette, old_active)
        else:
            self._rebuild_ui()
        self._refresh_settings_dialogs()

    def _export_csv(self):
        try:

            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv")],
                title=lang.t("dlg_export_csv"),
            )
            if not path:
                return

            pdlg = ctk.CTkToplevel(self)
            pdlg.title(lang.t("ui_export_title"))
            pdlg.transient(self)
            pdlg.grab_set()
            plbl = ctk.CTkLabel(
                pdlg, text=lang.t("ui_exporting"), font=theme.FONT_SMALL, text_color=theme.TEXT
            )
            plbl.pack(padx=24, pady=(20, 8))
            pbar = ctk.CTkProgressBar(pdlg, mode="indeterminate")
            pbar.pack(padx=24, pady=(0, 20))
            pbar.start()

            def work(progress):

                return export_service.export_csv(path)

            def on_done(n):
                pbar.stop()
                pdlg.destroy()
                self._show_status_banner(lang.t("ui_export_csv_ok"))

            def on_error(e):
                pbar.stop()
                pdlg.destroy()
                report_error(str(e))

            BackgroundTask(self, work, on_done=on_done, on_error=on_error).start()
        except Exception as e:
            report_error(str(e))

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
            log.debug_exc(logger)
        self.refresh_patients_db()

    def _sort_labels(self):
        return [
            ("name", lang.t("sort_name")),
            ("updated", lang.t("sort_updated")),
            ("localitate", lang.t("sort_localitate")),
            ("created", lang.t("sort_created")),
        ]

    def _sort_label(self):
        label = dict(self._sort_labels()).get(self.sort_by, lang.t("sort_name"))
        return label + (" \u2191" if self.sort_dir == "asc" else " \u2193")

    def _show_sort_menu(self):
        menu = tk.Menu(self, tearoff=0)
        for key, label in self._sort_labels():
            mark = " \u2713" if self.sort_by == key else ""
            menu.add_command(label=label + mark, command=functools.partial(self._sort_by, key))
        menu.add_separator()
        menu.add_command(
            label=lang.t("sort_ascending") + (" \u2713" if self.sort_dir == "asc" else ""),
            command=lambda: self._set_sort_dir("asc"),
        )
        menu.add_command(
            label=lang.t("sort_descending") + (" \u2713" if self.sort_dir == "desc" else ""),
            command=lambda: self._set_sort_dir("desc"),
        )
        try:
            x = self.sort_btn.winfo_rootx()
            y = self.sort_btn.winfo_rooty() + self.sort_btn.winfo_height()
            menu.tk_popup(x, y)
        except Exception:
            log.debug_exc(logger)
        finally:
            try:
                menu.grab_release()
            except Exception:
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
        except Exception:
            log.debug_exc(logger)
        self.refresh_patients_db()

    def _show_context_menu(self, event):
        """Right-click context menu for the patient card list."""
        if event is None:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=lang.t("ui_open"), command=self._open_patient_file)
        menu.add_command(label=lang.t("btn_edit_patient"), command=self._edit_current_patient)
        menu.add_command(label=lang.t("ui_copy_name"), command=self._copy_current_name)
        menu.add_separator()
        menu.add_command(label=lang.t("ui_delete"), command=self._delete_patient_db)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
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
        p = get_patient_service().get_patient(patient_id=self.selected_patient_id)
        if p:
            self.clipboard_clear()
            self.clipboard_append(p.get("name", ""))

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
            report_error(str(e))

    def _export_excel(self):
        try:

            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill

            settings = load_settings()
            initial = settings.get("export_fields")
            if not initial:
                initial = [k for k, _ in EXPORT_FIELDS]
            dlg = ExportFieldsDialog(self, EXPORT_FIELDS, initial=initial)
            self.wait_window(dlg)
            if not dlg.result:
                return
            chosen = dlg.result
            settings["export_fields"] = chosen
            save_settings(settings)

            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[(lang.t("ui_excel_file"), "*.xlsx")],
                title=lang.t("dlg_export_excel"),
            )
            if not path:
                return

            # progress dialog
            pdlg = ctk.CTkToplevel(self)
            pdlg.title(lang.t("ui_export_title"))
            pdlg.transient(self)
            pdlg.grab_set()
            plbl = ctk.CTkLabel(
                pdlg, text=lang.t("ui_exporting"), font=theme.FONT_SMALL, text_color=theme.TEXT
            )
            plbl.pack(padx=24, pady=(20, 8))
            pbar = ctk.CTkProgressBar(pdlg, mode="indeterminate")
            pbar.pack(padx=24, pady=(0, 20))
            pbar.start()

            def work(progress):
                wb = Workbook()
                ws = wb.active
                ws.title = "Pacienti"
                headers = [h for k, h in EXPORT_FIELDS if k in chosen]
                ws.append(headers)
                for c in range(1, len(headers) + 1):
                    cell = ws.cell(row=1, column=c)
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="4472C4")
                    cell.alignment = Alignment(
                        horizontal="center", vertical="center", wrap_text=True
                    )
                patients = get_patient_service().list_patients()
                total = len(patients)
                for i, p in enumerate(patients, 1):
                    ws.append([_field_value(p, k, i) for k in chosen])
                    if i % 50 == 0:
                        progress(lang.t("ui_export_progress", i=i, total=total))
                for row in ws.iter_rows(min_row=2):
                    for cell in row:
                        cell.alignment = Alignment(vertical="top", wrap_text=True)
                for idx in range(1, len(headers) + 1):
                    ws.column_dimensions[chr(64 + idx)].width = 18
                ws.freeze_panes = "A2"
                wb.save(path)
                return total

            def on_done(total):
                pbar.stop()
                pdlg.destroy()
                self._show_status_banner(lang.t("ui_export_excel_ok"))

            def on_error(e):
                pbar.stop()
                pdlg.destroy()
                report_error(str(e))

            def on_progress(msg):
                plbl.configure(text=msg)

            BackgroundTask(
                self, work, on_done=on_done, on_error=on_error, on_progress=on_progress
            ).start()
        except Exception as e:
            report_error(str(e))

    def _export_pdf(self):
        try:

            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")],
                title=lang.t("dlg_export_pdf"),
            )
            if not path:
                return

            pdlg = ctk.CTkToplevel(self)
            pdlg.title(lang.t("ui_export_title"))
            pdlg.transient(self)
            pdlg.grab_set()
            plbl = ctk.CTkLabel(
                pdlg, text=lang.t("ui_exporting"), font=theme.FONT_SMALL, text_color=theme.TEXT
            )
            plbl.pack(padx=24, pady=(20, 8))
            pbar = ctk.CTkProgressBar(pdlg, mode="indeterminate")
            pbar.pack(padx=24, pady=(0, 20))
            pbar.start()

            def work(progress):

                return export_service.export_pdf(path)

            def on_done(n):
                pbar.stop()
                pdlg.destroy()
                self._show_status_banner(lang.t("ui_export_ok"))

            def on_error(e):
                pbar.stop()
                pdlg.destroy()
                report_error(str(e))

            BackgroundTask(self, work, on_done=on_done, on_error=on_error).start()
        except Exception as e:
            report_error(str(e))

    def _export_word(self):
        try:

            path = filedialog.asksaveasfilename(
                defaultextension=".doc",
                filetypes=[(lang.t("ui_word_file"), "*.doc")],
                title=lang.t("dlg_export_word"),
            )
            if not path:
                return

            pdlg = ctk.CTkToplevel(self)
            pdlg.title(lang.t("ui_export_title"))
            pdlg.transient(self)
            pdlg.grab_set()
            plbl = ctk.CTkLabel(
                pdlg, text=lang.t("ui_exporting"), font=theme.FONT_SMALL, text_color=theme.TEXT
            )
            plbl.pack(padx=24, pady=(20, 8))
            pbar = ctk.CTkProgressBar(pdlg, mode="indeterminate")
            pbar.pack(padx=24, pady=(0, 20))
            pbar.start()

            def work(progress):

                return export_service.export_word(path)

            def on_done(n):
                pbar.stop()
                pdlg.destroy()
                self._show_status_banner(lang.t("ui_export_word_ok"))

            def on_error(e):
                pbar.stop()
                pdlg.destroy()
                report_error(str(e))

            BackgroundTask(self, work, on_done=on_done, on_error=on_error).start()
        except Exception as e:
            report_error(str(e))

    def _backup_now(self):
        folder = os.path.join(_data_dir(), "backup")
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(folder, "patients_" + stamp + ".db")

        dlg = ctk.CTkToplevel(self)
        dlg.title(lang.t("ui_backup"))
        dlg.transient(self)
        dlg.grab_set()
        lbl = ctk.CTkLabel(
            dlg, text=lang.t("ui_creating_backup"), font=theme.FONT_SMALL, text_color=theme.TEXT
        )
        lbl.pack(padx=24, pady=(20, 8))
        prog = ctk.CTkProgressBar(dlg, mode="indeterminate")
        prog.pack(padx=24, pady=(0, 20))
        prog.start()

        def work(progress):
            progress(lang.t("ui_checkpointing"))
            ok = get_backup_service().backup_to(dest)
            info = get_backup_service().verify(dest)[1] if ok else None
            try:
                att_src = os.path.join(_data_dir(), "attachments")
                if os.path.isdir(att_src):
                    att_dest = os.path.join(folder, "attachments_" + stamp)
                    if os.path.exists(att_dest):
                        shutil.rmtree(att_dest, ignore_errors=True)
                    shutil.copytree(att_src, att_dest)
            except Exception:
                log.debug_exc(logger)
            _prune_auto_backups(folder)
            return ok, info

        def on_done(result):
            prog.stop()
            dlg.destroy()
            ok, info = result
            if ok:
                messagebox.showinfo(
                    lang.t("app_name"),
                    lang.t("ui_backup_created", n=info, path=dest),
                )
            else:
                messagebox.showwarning(
                    lang.t("app_name"), lang.t("ui_backup_warn", info=lang.t("ui_failed"))
                )

        def on_error(e):
            prog.stop()
            dlg.destroy()
            report_error(str(e))

        def on_progress(msg):
            lbl.configure(text=msg)

        BackgroundTask(
            self, work, on_done=on_done, on_error=on_error, on_progress=on_progress
        ).start()

    def _restore_backup(self):
        try:
            folder = os.path.join(_data_dir(), "backup")
            if not os.path.isdir(folder):
                messagebox.showinfo(lang.t("app_name"), lang.t("msg_no_backups"))
                return
            files = sorted([f for f in os.listdir(folder) if f.endswith(".db")], reverse=True)
            if not files:
                messagebox.showinfo(lang.t("app_name"), lang.t("msg_no_backups"))
                return
            dlg = RestoreBackupDialog(self, folder, files)
            self.wait_window(dlg)
            if dlg.result:
                src = os.path.join(folder, dlg.result)
                ok, info = get_backup_service().verify(src)
                if not ok:
                    report_error(lang.t("msg_backup_verify_failed", info=str(info)))
                    return
                pdlg = ctk.CTkToplevel(self)
                pdlg.title(lang.t("ui_restore_title"))
                pdlg.transient(self)
                pdlg.grab_set()
                plbl = ctk.CTkLabel(
                    pdlg, text=lang.t("ui_restoring"), font=theme.FONT_SMALL, text_color=theme.TEXT
                )
                plbl.pack(padx=24, pady=(20, 8))
                pbar = ctk.CTkProgressBar(pdlg, mode="indeterminate")
                pbar.pack(padx=24, pady=(0, 20))
                pbar.start()

                def work(progress):
                    get_backup_service().pre_operation("restore")
                    get_backup_service().checkpoint()
                    shutil.copy2(src, get_database_service().path())
                    try:
                        get_database_service().init()
                    except Exception:
                        pass
                    return True

                def on_done(_):
                    pbar.stop()
                    pdlg.destroy()
                    self.refresh_patients_db()
                    messagebox.showinfo(lang.t("app_name"), lang.t("msg_restore_complete"))

                def on_error(e):
                    pbar.stop()
                    pdlg.destroy()
                    report_error(str(e))

                BackgroundTask(self, work, on_done=on_done, on_error=on_error).start()
        except Exception as e:
            report_error(str(e))

    def _import_data(self):
        try:
            get_backup_service().pre_operation("import")

            path = filedialog.askopenfilename(
                title=lang.t("dlg_import_title"),
                filetypes=[
                    ("CSV", "*.csv"),
                    (lang.t("ui_excel_file"), "*.xlsx"),
                    (lang.t("ui_all_files"), "*.*"),
                ],
            )
            if not path:
                return

            pdlg = ctk.CTkToplevel(self)
            pdlg.title(lang.t("ui_import_title"))
            pdlg.transient(self)
            pdlg.grab_set()
            plbl = ctk.CTkLabel(
                pdlg, text=lang.t("ui_importing"), font=theme.FONT_SMALL, text_color=theme.TEXT
            )
            plbl.pack(padx=24, pady=(20, 8))
            pbar = ctk.CTkProgressBar(pdlg, mode="indeterminate")
            pbar.pack(padx=24, pady=(0, 20))
            pbar.start()

            def work(progress):
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
                        pid = get_patient_service().ensure_patient_exists(name)
                        if pid is not None:
                            get_patient_service().update_patient(
                                pid,
                                localitate=loc,
                                diagnostic=diag,
                                objective=obj,
                                evaluation=eva,
                                observation=obs,
                            )
                            count += 1
                    except Exception:
                        log.debug_exc(logger)
                return count

            def on_done(count):
                pbar.stop()
                pdlg.destroy()
                self.refresh_patients_db()
                messagebox.showinfo(lang.t("app_name"), lang.t("ui_imported", n=count))

            def on_error(e):
                pbar.stop()
                pdlg.destroy()
                report_error(str(e))

            BackgroundTask(self, work, on_done=on_done, on_error=on_error).start()
        except Exception as e:
            report_error(str(e))

    def _show_trash(self):
        dlg = TrashDialog(self)
        self.wait_window(dlg)
        self.refresh_patients_db()

    def _auto_backup(self):
        try:
            folder = os.path.join(_data_dir(), "backup")
            os.makedirs(folder, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d")
            dest = os.path.join(folder, "patients_auto_" + stamp + ".db")
            if not os.path.exists(dest):
                get_backup_service().backup_to(dest)
            _prune_auto_backups(folder)
        except Exception:
            log.debug_exc(logger)

    def _add_patient_db(self):
        dlg = AddPatientDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            try:
                existing = get_patient_service().get_patient(name=dlg.result["name"])
                if existing:
                    if messagebox.askyesno(lang.t("app_name"), lang.t("confirm_patient_exists")):
                        pid = existing["id"]
                        self._open_patient_by_id(pid)
                        return
                    else:
                        return
                pid, _validation = get_patient_service().create_patient(
                    dlg.result["name"],
                    dlg.result["localitate"],
                    sex=dlg.result.get("sex", ""),
                    dob=dlg.result.get("dob", ""),
                    diagnostic=dlg.result["diagnostic"],
                    objective=dlg.result["objective"],
                    evaluation=dlg.result["evaluation"],
                    observation=dlg.result["observation"],
                )
                self.refresh_patients_db()
                self.known_patients = get_patient_service().get_patient_names()
            except Exception as e:
                report_error(str(e))


_SINGLE_INSTANCE_PORT = 47832


def _try_acquire_instance():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", _SINGLE_INSTANCE_PORT))
        s.listen(1)
        return s, True
    except OSError:
        try:
            s.close()
        except Exception:
            pass
        return None, False


def main():
    sock, primary = _try_acquire_instance()
    if not primary:
        try:
            c = socket.create_connection(("127.0.0.1", _SINGLE_INSTANCE_PORT), timeout=2)
            c.sendall(b"focus\n")
            c.close()
        except Exception:
            pass
        try:
            messagebox.showinfo(lang.t("app_name"), lang.t("msg_already_running"))
        except Exception:
            pass
        return

    app_holder: dict[str, App | None] = {"app": None}

    def _focus_app():
        app = app_holder.get("app")
        if app is None:
            return
        try:
            app.deiconify()
            app.lift()
            app.focus_force()
        except Exception:
            pass

    def _listener():
        while True:
            try:
                conn, _ = sock.accept()
                data = conn.recv(64)
                conn.close()
                if b"focus" in data:
                    a = app_holder.get("app")
                    if a is not None:
                        try:
                            a.after(0, _focus_app)
                        except Exception:
                            pass
            except Exception:
                break

    threading.Thread(target=_listener, daemon=True).start()

    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook
    try:
        ctk.deactivate_automatic_dpi_awareness()
    except Exception:
        log.debug_exc(logger)
    try:
        app = App()
    except Exception as exc:
        _log_uncaught(*sys.exc_info())
        _show_crash_dialog(exc)
        return
    app_holder["app"] = app
    app.mainloop()
    try:
        sock.close()
    except Exception:
        pass


_SELF_TEST_IMPORTS = ("customtkinter", "PIL", "fitz", "openpyxl", "darkdetect")


def run_self_test(argv: list[str] | None = None) -> int:
    """Headless startup validation used by release smoke tests.

    Initialises the database, runs the diagnostics checks and verifies that
    optional bundled dependencies can be imported.  A JSON report is written
    so a windowed executable can communicate results without a console.
    """
    args = list(sys.argv if argv is None else argv)
    report_path = os.path.join(_data_dir(), "self_test.json")
    if "--self-test-report" in args:
        index = args.index("--self-test-report")
        if index + 1 < len(args):
            report_path = args[index + 1]

    checks: list[tuple[str, bool, str]] = []
    try:
        get_database_service().init()
        checks.append(("Database init", True, get_database_service().path()))
    except Exception as e:
        log.debug_exc(logger)
        checks.append(("Database init", False, str(e)))

    checks.extend(run_startup_checks())

    for module in _SELF_TEST_IMPORTS:
        try:
            importlib.import_module(module)
            checks.append((f"Import {module}", True, "OK"))
        except Exception as e:
            log.debug_exc(logger)
            checks.append((f"Import {module}", False, str(e)))

    ok = all(passed for _name, passed, _detail in checks)
    payload = {
        "ok": ok,
        "version": __version__,
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "data_dir": _data_dir(),
        "checks": [
            {"name": name, "ok": passed, "detail": detail} for name, passed, detail in checks
        ],
    }
    try:
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except Exception:
        log.debug_exc(logger)
    logger.info("self-test %s: %s", "passed" if ok else "FAILED", report_path)
    if not ok:
        for name, passed, detail in checks:
            if not passed:
                logger.error("self-test check failed: %s - %s", name, detail)
    try:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(run_self_test(sys.argv))
    main()
