from .common import ctk, lang, tk


class RestoreBackupDialog(ctk.CTkToplevel):
    def __init__(self, master, folder, files):
        super().__init__(master)
        self.title(lang.t("dlg_restore_backup"))
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

        ctk.CTkButton(btns, text=lang.t("ui_restore"), width=80, command=_ok).pack(
            side="left", padx=2
        )
        ctk.CTkButton(btns, text=lang.t("btn_cancel"), width=80, command=self.destroy).pack(
            side="left", padx=2
        )
