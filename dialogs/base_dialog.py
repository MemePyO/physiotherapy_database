"""Base dialog class for themed CTk dialogs."""

import customtkinter as ctk

import lang
import theme
from ui import ttk_style

from .common import dialog_scale, fit_to_content


class BaseDialog(ctk.CTkToplevel):
    """Common scaffolding for modal themed dialogs."""

    def __init__(self, master, title, width=400, height=200):
        super().__init__(master)
        self._min_width = width
        self._min_height = height
        ttk_style.apply(self, scale=dialog_scale(master))
        self.title(title)
        self.geometry("%dx%d" % (width, height))
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        # center over parent
        try:
            self.update_idletasks()
            x = master.winfo_rootx() + (master.winfo_width() - width) // 2
            y = master.winfo_rooty() + (master.winfo_height() - height) // 2
            self.geometry("+%d+%d" % (x, y))
        except Exception:
            pass
        # Children are added by the subclass after this __init__, so grow to
        # fit them once the event loop has built the layout.
        try:
            self.after_idle(lambda: fit_to_content(self, width, height))
        except Exception:
            pass

    def _add_buttons(self, ok_text=None, cancel_text=None, ok_command=None, cancel_command=None):
        if ok_text is None:
            ok_text = lang.t("btn_ok")
        if cancel_text is None:
            cancel_text = lang.t("btn_cancel")
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=12, pady=12)
        if cancel_text:
            ctk.CTkButton(
                btn_frame,
                text=cancel_text,
                width=90,
                fg_color=theme.MUTED_BTN,
                hover_color=theme.MUTED_BTN_HOVER,
                command=cancel_command or self.destroy,
            ).pack(side="right", padx=(4, 0))
        if ok_text:
            ctk.CTkButton(
                btn_frame, text=ok_text, width=90, fg_color=theme_color(), command=ok_command
            ).pack(side="right")
        return btn_frame


def theme_color():
    return theme.ACCENT
