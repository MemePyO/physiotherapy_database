"""Base dialog class for themed CTk dialogs."""

import customtkinter as ctk


class BaseDialog(ctk.CTkToplevel):
    """Common scaffolding for modal themed dialogs."""

    def __init__(self, master, title, width=400, height=200):
        super().__init__(master)
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

    def _add_buttons(
        self, ok_text="OK", cancel_text="Cancel", ok_command=None, cancel_command=None
    ):
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=12, pady=12)
        if cancel_text:
            ctk.CTkButton(
                btn_frame,
                text=cancel_text,
                width=90,
                fg_color="#6b7280",
                hover_color="#4b5563",
                command=cancel_command or self.destroy,
            ).pack(side="right", padx=(4, 0))
        if ok_text:
            ctk.CTkButton(
                btn_frame, text=ok_text, width=90, fg_color=theme_color(), command=ok_command
            ).pack(side="right")
        return btn_frame


def theme_color():
    import theme

    return theme.ACCENT
