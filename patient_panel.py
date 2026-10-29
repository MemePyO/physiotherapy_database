"""Embedded patient file panel (dashboard style)."""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import db
import lang
import theme


def _initials(name):
    parts = (name or "").split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][:1] + parts[-1][:1]).upper()


class PatientFilePanel(ctk.CTkFrame):
    def __init__(self, master, patient_id, on_close=None):
        super().__init__(master, fg_color=theme.PANEL, corner_radius=theme.PANEL_RADIUS)
        self.patient_id = patient_id
        self.on_close_callback = on_close
        self._dirty = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.patient = db.get_patient(patient_id=patient_id)
        if not self.patient:
            self.destroy()
            return

        self._build_header()
        self._build_sections()
        self._build_footer()

    # ---- header ----
    def _build_header(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", padx=theme.PADDING, pady=(theme.PADDING, 8))
        frame.grid_columnconfigure(1, weight=1)

        # avatar
        av = ctk.CTkLabel(frame, text=_initials(self.patient['name']), width=theme.AVATAR_SIZE,
                          height=theme.AVATAR_SIZE, corner_radius=theme.AVATAR_SIZE // 2,
                          fg_color=theme.ACCENT, text_color="white",
                          font=ctk.CTkFont(size=14, weight="bold"))
        av.grid(row=0, column=0, rowspan=4, padx=(0, 12))

        name_lbl = ctk.CTkLabel(frame, text=self.patient['name'], font=ctk.CTkFont(size=16, weight="bold"),
                                text_color=theme.TEXT)
        name_lbl.grid(row=0, column=1, sticky="w")
        self.name_label = name_lbl

        # Info line: DOB, Sex, Locality
        dob = self.patient.get('dob', '') or 'NA'
        sex = self.patient.get('sex', '') or 'NA'
        loc = self.patient.get('localitate', '') or 'NA'
        info_text = f"DOB: {dob}   |   Sex: {sex}   |   Locality: {loc}"
        info_lbl = ctk.CTkLabel(frame, text=info_text, font=theme.FONT_SUB, text_color=theme.MUTED)
        info_lbl.grid(row=1, column=1, sticky="w")
        self.info_label = info_lbl

        # Main diagnostic in header
        diag = self.patient.get('diagnostic', '') or ''
        first_line = diag.split(chr(10))[0].strip() if diag else ''
        main_diag = first_line if first_line else 'NA'
        diag_lbl = ctk.CTkLabel(frame, text="Diagnostic: " + main_diag, font=theme.FONT_BOLD, text_color=theme.ACCENT)
        diag_lbl.grid(row=2, column=1, sticky="w")
        self.diag_header_label = diag_lbl

        self.modified_label = ctk.CTkLabel(frame, text="Last modified: " + (self.patient.get('updated_at') or 'NA'),
                                          font=theme.FONT_SMALL, text_color=theme.MUTED)
        self.modified_label.grid(row=3, column=1, sticky="w", pady=(2, 0))

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.grid(row=0, column=2, rowspan=4, sticky="e")
        ctk.CTkButton(btns, text="Edit", width=70, fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK,
                      command=self._edit_patient_info).pack(side="left", padx=2)

    def _refresh_header_info(self):
        dob = self.patient.get('dob', '') or 'NA'
        sex = self.patient.get('sex', '') or 'NA'
        loc = self.patient.get('localitate', '') or 'NA'
        try:
            self.info_label.configure(text=f"DOB: {dob}   |   Sex: {sex}   |   Locality: {loc}")
        except Exception:
            pass
        diag = self.patient.get('diagnostic', '') or ''
        first_line = diag.split(chr(10))[0].strip() if diag else ''
        main_diag = first_line if first_line else 'NA'
        try:
            self.diag_header_label.configure(text="Diagnostic: " + main_diag)
        except Exception:
            pass

    # ---- sections ----
    def _build_sections(self):
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.grid(row=1, column=0, sticky="nsew", padx=theme.PADDING, pady=(0, 8))
        container.grid_columnconfigure(0, weight=1)

        sections = [("diagnostic", "Diagnostic", theme.SEC_DIAG),
                    ("objective", "Obiectiv", theme.SEC_OBJ),
                    ("evaluation", "Evaluare", theme.SEC_EVAL),
                    ("observation", "Observație", theme.SEC_OBS)]
        self.texts = {}
        self.count_labels = {}
        for idx, (field, title, color) in enumerate(sections):
            frame = ctk.CTkFrame(container, fg_color=theme.PANEL, corner_radius=theme.CARD_RADIUS,
                                 border_width=1, border_color=theme.BORDER)
            frame.grid(row=idx, column=0, sticky="ew", pady=(0, 10))
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(1, weight=1)

            # colored title bar
            bar = ctk.CTkFrame(frame, fg_color=color, corner_radius=0, height=30)
            bar.grid(row=0, column=0, sticky="ew")
            bar.grid_propagate(False)
            bar.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(bar, text=title, text_color="white", font=theme.FONT_SECTION).grid(row=0, column=0, sticky="w", padx=12)
            cnt = ctk.CTkLabel(bar, text="", text_color="white", font=theme.FONT_SMALL)
            cnt.grid(row=0, column=1, sticky="e", padx=12)
            self.count_labels[field] = cnt

            txt = ctk.CTkTextbox(frame, height=110, corner_radius=0, border_width=0,
                                 fg_color=theme.PANEL, text_color=theme.TEXT, font=theme.FONT_BODY)
            txt.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
            val = self.patient.get(field, '') or ''
            txt.insert("1.0", val)
            txt.bind("<KeyRelease>", lambda e, f=field, t=txt: (self._on_text_change(f, t), self.mark_dirty()))
            setattr(self, field + "_text", txt)
            self._update_count(field, txt)

            # placeholder
            self._add_placeholder(txt, "Empty..." if not val else None)

        # ensure at least min height for the scroll container
        container.grid_rowconfigure(len(sections) - 1, weight=0)

    def _add_placeholder(self, txt, text):
        if not text:
            return
        lbl = ctk.CTkLabel(txt, text=text, text_color=theme.MUTED, font=theme.FONT_SMALL)
        lbl.place(relx=0.02, rely=0.05)
        def _hide(e=None):
            if txt.get("1.0", "end-1c").strip():
                lbl.place_forget()
            else:
                lbl.place(relx=0.02, rely=0.05)
        txt.bind("<KeyRelease>", lambda e, f=None: (_hide(), None)[1] or None, add="+")
        # call once
        _hide()

    def _on_text_change(self, field, txt):
        self._dirty = True
        self._update_count(field, txt)
        self._update_title_star()
        # placeholder hide
        try:
            pass
        except Exception:
            pass

    def _update_count(self, field, txt):
        try:
            content = txt.get("1.0", "end-1c")
            chars = len(content)
            lines = content.count("\n") + (1 if content.strip() else 0)
            if content == "":
                lines = 0
            self.count_labels[field].configure(text=f"{chars} ch · {lines} ln")
        except Exception:
            pass

    def _update_title_star(self):
        pass

    # ---- footer ----
    def _build_footer(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", padx=theme.PADDING, pady=(0, theme.PADDING))
        frame.grid_columnconfigure(0, weight=1)
        self.dirty_label = ctk.CTkLabel(frame, text="", text_color=theme.DANGER, font=theme.FONT_SMALL)
        self.dirty_label.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(frame, text="💾  Save Patient Record", width=180, height=36,
                      fg_color=theme.ACCENT, hover_color=theme.ACCENT_DARK, font=theme.FONT_BOLD,
                      command=self._save_all).grid(row=0, column=1, sticky="e")

    # ---- save ----
    def _save_all(self):
        try:
            db.update_patient(self.patient_id,
                diagnostic=self.diagnostic_text.get("1.0", "end-1c"),
                objective=self.objective_text.get("1.0", "end-1c"),
                evaluation=self.evaluation_text.get("1.0", "end-1c"),
                observation=self.observation_text.get("1.0", "end-1c"))
            self.patient = db.get_patient(patient_id=self.patient_id)
            self._dirty = False
            self.dirty_label.configure(text="")
            self._refresh_header_info()
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
                db.update_patient(self.patient_id, name=dlg.result['name'], localitate=dlg.result['localitate'], sex=dlg.result.get('sex', ''), dob=dlg.result.get('dob', ''))
                self.patient = db.get_patient(patient_id=self.patient_id)
                self.name_label.configure(text=self.patient['name'])
                self._refresh_header_info()
                try:
                    self.modified_label.configure(text="Last modified: " + (self.patient.get('updated_at') or 'NA'))
                except Exception:
                    pass
                if self.on_close_callback:
                    self.on_close_callback()
            except Exception as e:
                messagebox.showerror(lang.t("app_name"), str(e))

    def mark_dirty(self):
        self._dirty = True
        self.dirty_label.configure(text="Unsaved changes *")

    def is_dirty(self):
        return self._dirty


# ---- edit dialog (same as before, with locality combobox) ----
class EditPatientDialog(ctk.CTkToplevel):
    def __init__(self, master, patient):
        super().__init__(master)
        self.title(lang.t("dlg_edit_patient"))
        self.geometry("400x280")
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

        ctk.CTkLabel(self, text="Sex:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.entry_sex = ctk.CTkComboBox(self, values=["NA", "M", "F"])
        self.entry_sex.set(patient.get('sex', '') or "NA")
        self.entry_sex.grid(row=2, column=1, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self, text="Date of birth (DD.MM.YYYY):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.entry_dob = ctk.CTkEntry(self)
        self.entry_dob.insert(0, patient.get('dob', '') or '')
        self.entry_dob.grid(row=3, column=1, sticky="ew", padx=10, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="e", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text=lang.t("btn_ok"), width=80, command=self._ok).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text=lang.t("btn_cancel"), width=80, command=self.destroy).pack(side="left", padx=2)
        self.entry_name.focus()

    def _ok(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showerror(lang.t("app_name"), lang.t("err_patient_name_required"))
            return
        sex = self.entry_sex.get().strip()
        if sex == "NA":
            sex = ""
        self.result = {"name": name, "localitate": self.entry_loc.get().strip(), "sex": sex, "dob": self.entry_dob.get().strip()}
        self.destroy()
