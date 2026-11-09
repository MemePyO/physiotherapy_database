from .common import *

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
        ctk.CTkLabel(self, text="Choose format:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w"
        )
        self.fmt = tk.StringVar(value="excel")
        for i, (val, lbl) in enumerate(
            [
                ("excel", "Excel (.xlsx)"),
                ("csv", "CSV / Access"),
                ("pdf", "PDF"),
                ("word", "Word (.doc)"),
            ]
        ):
            ctk.CTkRadioButton(self, text=lbl, variable=self.fmt, value=val).grid(
                row=i + 1, column=0, padx=20, pady=4, sticky="w"
            )
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=6, column=0, sticky="e", padx=10, pady=10)
        ctk.CTkButton(btns, text="OK", width=80, command=self._ok).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Cancel", width=80, command=self.destroy).pack(side="left", padx=2)

    def _ok(self):
        self.result = self.fmt.get()
        self.destroy()
