"""Themed input dialog replacing tkinter.simpledialog."""
import customtkinter as ctk
from .base_dialog import BaseDialog


class CTkInputDialog(BaseDialog):
    """A simple themed dialog that asks for a single string value."""

    def __init__(self, master, title, prompt, initialvalue="", validate=None):
        super().__init__(master, title, width=360, height=160)
        self._result = None
        self._validate = validate

        ctk.CTkLabel(self, text=prompt, font=("Segoe UI", 11), text_color="#333",
                     anchor="w").pack(padx=16, pady=(16, 4), fill="x")
        self.entry = ctk.CTkEntry(self, width=320)
        self.entry.pack(padx=16, pady=(0, 8))
        self.entry.insert(0, initialvalue or "")
        self.entry.focus_set()

        self.err_label = ctk.CTkLabel(self, text="", text_color="#c0392b",
                                     font=("Segoe UI", 10), anchor="w")
        self.err_label.pack(padx=16, fill="x")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=12, pady=12)
        ctk.CTkButton(btns, text="Cancel", width=90, fg_color="#6b7280",
                      hover_color="#4b5563", command=self._cancel).pack(side="right", padx=(4, 0))
        ctk.CTkButton(btns, text="OK", width=90, command=self._ok).pack(side="right")

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        self.wait_window(self)

    def _ok(self):
        val = self.entry.get()
        if self._validate:
            err = self._validate(val)
            if err:
                self.err_label.configure(text=err)
                return
        self._result = val
        self.destroy()

    def _cancel(self):
        self._result = None
        self.destroy()

    def get_input(self):
        return self._result


def ask_string(master, title, prompt, initialvalue="", validate=None):
    """Convenience wrapper returning the entered string or None."""
    dlg = CTkInputDialog(master, title, prompt, initialvalue=initialvalue, validate=validate)
    return dlg.get_input()