"""Patient detail page with diagnostic, objective, evaluation and observation text areas."""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import db
import lang


class PatientPage(ctk.CTkToplevel):
    def __init__(self, master, patient_id, on_close=None):
        super().__init__(master)
        self.patient_id = patient_id
        self.on_close_callback = on_close
        self._dirty = False

        self.title(lang.t("patient_page_title"))
        self.geometry("900x640")
        self.minsize(760, 520)
        self.transient(master)
        self.grab_set()

        self.patient = db.get_patient(patient_id=patient_id)
        if not self.patient:
            self.destroy()
            return

        self.title(f"{lang.t('patient_page_title')} - {self.patient['name']}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Fixed header bar (always visible)
        self._build_header()

        # 2x2 sections grid that grows with the window
        self.sections_frame = ctk.CTkFrame(self)
        self.sections_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.sections_frame.grid_columnconfigure(0, weight=1)
        self.sections_frame.grid_columnconfigure(1, weight=1)
        self.sections_frame.grid_rowconfigure(0, weight=1)
        self.sections_frame.grid_rowconfigure(1, weight=1)

        fields = [("diagnostic", lang.t("section_diagnoses"), 0, 0),
                  ("objective", lang.t("section_objectives"), 0, 1),
                  ("evaluation", lang.t("section_evaluations"), 1, 0),
                  ("observation", lang.t("section_observations"), 1, 1)]
        self.texts = {}
        self.count_labels = {}
        for field, title, r, c in fields:
            self._build_section(self.sections_frame, title, field, r, c)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-s>", lambda e: self._save_all() or "break")

    def _build_header(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        frame.grid_columnconfigure(1, weight=1)

        self.name_label = ctk.CTkLabel(frame, text=self.patient['name'], font=ctk.CTkFont(size=16, weight="bold"))
        self.name_label.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=5)

        self.loc_label = ctk.CTkLabel(frame, text=self.patient.get('localitate', ''), font=ctk.CTkFont(size=14))
        self.loc_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        self.modified_label = ctk.CTkLabel(frame, text=("Last modified: " + (self.patient.get('updated_at') or '')), text_color="#555555", font=ctk.CTkFont(size=11))
        self.modified_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 5))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.grid(row=0, column=2, sticky="e", padx=10, pady=5)
        ctk.CTkButton(btns, text=lang.t("btn_edit_patient"), width=110, command=self._edit_patient_info).pack(side="left", padx=2)
        ctk.CTkButton(btns, text=lang.t("btn_save_all"), width=90, command=self._save_all).pack(side="left", padx=2)

    def _build_section(self, parent, title, field, row, col):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w")
        count_lbl = ctk.CTkLabel(header, text="", text_color="#555555", font=ctk.CTkFont(size=11))
        count_lbl.grid(row=0, column=1, sticky="e")
        self.count_labels[field] = count_lbl

        txt = ctk.CTkTextbox(frame)
        txt.grid(row=1, column=0, sticky="nsew", padx=5, pady=(2, 5))
        val = self.patient.get(field, '') or ''
        txt.insert("1.0", val)
        txt.bind("<KeyRelease>", lambda e, f=field, t=txt: self._on_text_change(f, t))
        setattr(self, field + "_text", txt)
        self._update_count(field, txt)

    def _on_text_change(self, field, txt):
        self._dirty = True
        self._update_count(field, txt)
        self._update_title()

    def _update_count(self, field, txt):
        try:
            content = txt.get("1.0", "end-1c")
            chars = len(content)
            lines = content.count("\n") + (1 if content.strip() else 0)
            if content == "":
                lines = 0
            self.count_labels[field].configure(text=f"{chars} ch \u00b7 {lines} lines")
        except Exception:
            pass

    def _update_title(self):
        base = f"{lang.t('patient_page_title')} - {self.patient['name']}"
        self.title(base + (" *" if self._dirty else ""))

    def _save_all(self):
        try:
            db.update_patient(self.patient_id,
                diagnostic=self.diagnostic_text.get("1.0", "end-1c"),
                objective=self.objective_text.get("1.0", "end-1c"),
                evaluation=self.evaluation_text.get("1.0", "end-1c"),
                observation=self.observation_text.get("1.0", "end-1c"))
            self.patient = db.get_patient(patient_id=self.patient_id)
            self._dirty = False
            self._update_title()
            try:
                self.modified_label.configure(text="Last modified: " + (self.patient.get('updated_at') or ''))
            except Exception:
                pass
            if self.on_close_callback:
                self.on_close_callback()
            messagebox.showinfo(lang.t("app_name"), lang.t("msg_saved"))
        except Exception as e:
            messagebox.showerror(lang.t("app_name"), str(e))

    def _edit_patient_info(self):
        dlg = EditPatientDialog(self, self.patient)
        self.wait_window(dlg)
        if dlg.result:
            try:
                db.update_patient(self.patient_id, name=dlg.result['name'], localitate=dlg.result['localitate'])
                self.patient = db.get_patient(patient_id=self.patient_id)
                self.name_label.configure(text=self.patient['name'])
                self.loc_label.configure(text=self.patient.get('localitate', ''))
                self._update_title()
                if self.on_close_callback:
                    self.on_close_callback()
            except Exception as e:
                messagebox.showerror(lang.t("app_name"), str(e))

    def _on_close(self):
        if self._dirty:
            if messagebox.askyesno(lang.t("app_name"), "Save changes before closing?"):
                self._save_all()
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


class EditPatientDialog(ctk.CTkToplevel):
    def __init__(self, master, patient):
        super().__init__(master)
        self.title(lang.t("dlg_edit_patient"))
        self.geometry("400x200")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.result = None

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=lang.t("label_patient_name") + ":").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.entry_name = ctk.CTkEntry(self)
        self.entry_name.insert(0, patient.get('name', ''))
        self.entry_name.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(self, text=lang.t("label_localitate") + ":").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.entry_loc = ctk.CTkComboBox(self, values=db.get_localities())
        self.entry_loc.set(patient.get('localitate', ''))
        self.entry_loc.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="e", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text=lang.t("btn_ok"), width=80, command=self._ok).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text=lang.t("btn_cancel"), width=80, command=self.destroy).pack(side="left", padx=2)

        self.entry_name.focus()

    def _ok(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showerror(lang.t("app_name"), lang.t("err_patient_name_required"))
            return
        self.result = {
            "name": name,
            "localitate": self.entry_loc.get().strip()
        }
        self.destroy()
''