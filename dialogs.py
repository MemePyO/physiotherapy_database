"""Dialog windows for the patient database app."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

import db
import lang
import theme
import utils
import log
logger = log.get_logger(__name__)
from utils import _validate_dob, _norm


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
        if not _validate_dob(self.entry_dob.get()):
            messagebox.showerror(lang.t("app_name"), "Date of birth must be DD.MM.YYYY (e.g. 12.05.1990)")
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
        def _restore_all():
            for iid in list(tree.get_children()):
                try:
                    db.restore_deleted(int(iid))
                    tree.delete(iid)
                except Exception as e:
                    messagebox.showerror(lang.t("app_name"), str(e))
        def _empty_trash():
            if not messagebox.askyesno(lang.t("app_name"), "Permanently delete ALL deleted patients?"):
                return
            conn = db._get_conn()
            conn.execute("DELETE FROM deleted_patients")
            conn.commit()
            conn.close()
            for iid in list(tree.get_children()):
                tree.delete(iid)
        ctk.CTkButton(btns, text="Restore", width=80, command=_restore).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Restore all", width=90, command=_restore_all).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Purge", width=70, fg_color="#c0392b", command=_purge).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Empty trash", width=90, fg_color="#c0392b", command=_empty_trash).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Close", width=70, command=self.destroy).pack(side="left", padx=2)

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
