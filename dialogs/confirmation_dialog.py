"""Themed confirmation dialog replacing tkinter.messagebox.askyesno."""

import customtkinter as ctk

from .base_dialog import BaseDialog


class CTkConfirmationDialog(BaseDialog):
    def __init__(self, master, title, message, ok_text="Yes", cancel_text="No"):
        super().__init__(master, title, width=360, height=150)
        self._result = False

        ctk.CTkLabel(
            self,
            text=message,
            font=("Segoe UI", 11),
            text_color="#333",
            anchor="w",
            wraplength=320,
            justify="left",
        ).pack(padx=16, pady=(20, 8), fill="x")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=12, pady=12)
        ctk.CTkButton(
            btns,
            text=cancel_text,
            width=90,
            fg_color="#6b7280",
            hover_color="#4b5563",
            command=self._no,
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(btns, text=ok_text, width=90, command=self._yes).pack(side="right")

        self.bind("<Return>", lambda e: self._yes())
        self.bind("<Escape>", lambda e: self._no())
        self.wait_window(self)

    def _yes(self):
        self._result = True
        self.destroy()

    def _no(self):
        self._result = False
        self.destroy()

    def get_result(self):
        return self._result


def ask_yes_no(master, title, message, ok_text="Yes", cancel_text="No"):
    dlg = CTkConfirmationDialog(master, title, message, ok_text=ok_text, cancel_text=cancel_text)
    return dlg.get_result()
