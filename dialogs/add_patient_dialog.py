from .common import _validate_dob, ctk, db, lang, messagebox


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

        ctk.CTkLabel(scroll, text=lang.t("label_patient_name") + ":").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        self.entry_name = ctk.CTkEntry(scroll)
        self.entry_name.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(scroll, text=lang.t("label_localitate") + ":").grid(
            row=2, column=0, sticky="w", pady=(0, 2)
        )
        self.entry_loc = ctk.CTkComboBox(scroll, values=db.get_localities())
        self.entry_loc.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(scroll, text="Sex:").grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.entry_sex = ctk.CTkComboBox(scroll, values=["NA", "M", "F"])
        self.entry_sex.set("NA")
        self.entry_sex.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(scroll, text="Date of birth (DD.MM.YYYY):").grid(
            row=6, column=0, sticky="w", pady=(0, 2)
        )
        self.entry_dob = ctk.CTkEntry(scroll)
        self.entry_dob.grid(row=7, column=0, sticky="ew", pady=(0, 8))

        fields = [
            ("diagnostic", lang.t("label_diagnostic")),
            ("objective", lang.t("label_objective")),
            ("evaluation", lang.t("label_evaluation")),
            ("observation", lang.t("label_observation")),
        ]
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
        ctk.CTkButton(btn_frame, text=lang.t("btn_ok"), width=80, command=self._ok).pack(
            side="left", padx=2
        )
        ctk.CTkButton(btn_frame, text=lang.t("btn_cancel"), width=80, command=self.destroy).pack(
            side="left", padx=2
        )

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.entry_name.focus()

    def _ok(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showerror(lang.t("app_name"), lang.t("err_patient_name_required"))
            return
        if not _validate_dob(self.entry_dob.get()):
            messagebox.showerror(
                lang.t("app_name"), "Date of birth must be DD.MM.YYYY (e.g. 12.05.1990)"
            )
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
