from .common import ctk, lang, theme, tk


class ExportFieldsDialog(ctk.CTkToplevel):
    """Let the user choose which fields to export and their column order."""

    def __init__(self, master, field_specs, initial=None):
        super().__init__(master)
        self.title("Export fields")
        self.geometry("460x420")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.result = None
        self.field_specs = field_specs  # list of (key, header)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=lang.t("ui_available_fields"), font=theme.FONT_BOLD).grid(
            row=0, column=0, padx=8, pady=(8, 2)
        )
        ctk.CTkLabel(self, text=lang.t("ui_selected_in_order"), font=theme.FONT_BOLD).grid(
            row=0, column=2, padx=8, pady=(8, 2)
        )

        self.avail = tk.Listbox(self, selectmode="single", exportselection=False)
        self.avail.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.sel = tk.Listbox(self, selectmode="single", exportselection=False)
        self.sel.grid(row=1, column=2, sticky="nsew", padx=8, pady=4)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=1, column=1, padx=4)
        ctk.CTkButton(btns, text=">", width=40, command=self._add).pack(pady=4)
        ctk.CTkButton(btns, text="<", width=40, command=self._remove).pack(pady=4)
        ctk.CTkButton(btns, text="\u2191", width=40, command=self._up).pack(pady=4)
        ctk.CTkButton(btns, text="\u2193", width=40, command=self._down).pack(pady=4)

        # populate
        selected_keys = list(initial) if initial else [k for k, _ in field_specs]
        avail_keys = [k for k, _ in field_specs if k not in selected_keys]
        for k in avail_keys:
            self.avail.insert("end", self._label(k))
        for k in selected_keys:
            self.sel.insert("end", self._label(k))

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.grid(row=2, column=0, columnspan=3, sticky="e", padx=8, pady=8)
        ctk.CTkButton(bf, text="OK", width=80, command=self._ok).pack(side="left", padx=2)
        ctk.CTkButton(bf, text="Cancel", width=80, command=self.destroy).pack(side="left", padx=2)

    def _label(self, key):
        for k, h in self.field_specs:
            if k == key:
                return h + "  [" + k + "]"
        return key

    def _key_of(self, text):
        # text like "Header  [key]"
        if "[" in text and text.endswith("]"):
            return text[text.rfind("[") + 1 : -1]
        return text

    def _add(self):
        sel = self.avail.curselection()
        if not sel:
            return
        text = self.avail.get(sel[0])
        self.avail.delete(sel[0])
        self.sel.insert("end", text)

    def _remove(self):
        sel = self.sel.curselection()
        if not sel:
            return
        text = self.sel.get(sel[0])
        self.sel.delete(sel[0])
        self.avail.insert("end", text)

    def _up(self):
        sel = self.sel.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        text = self.sel.get(i)
        self.sel.delete(i)
        self.sel.insert(i - 1, text)
        self.sel.selection_set(i - 1)

    def _down(self):
        sel = self.sel.curselection()
        if not sel or sel[0] == self.sel.size() - 1:
            return
        i = sel[0]
        text = self.sel.get(i)
        self.sel.delete(i)
        self.sel.insert(i + 1, text)
        self.sel.selection_set(i + 1)

    def _ok(self):
        keys = [self._key_of(self.sel.get(i)) for i in range(self.sel.size())]
        self.result = keys
        self.destroy()
