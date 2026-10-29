"""Single, in-window hover tooltips.

Only one tooltip can exist at a time, and it is a label placed inside the app
window instead of a separate top-level window, so it can never be left behind
on the desktop when the pointer moves away quickly.
"""
import customtkinter as ctk

import theme

# Currently visible tooltip: {"label": widget | None, "job": (window, id) | None}
_state = {"label": None, "job": None}


def hide_tooltip():
    """Remove the visible tooltip and cancel its auto-hide timer, if any."""
    job = _state.get("job")
    if job is not None:
        window, job_id = job
        try:
            window.after_cancel(job_id)
        except Exception:
            pass
        _state["job"] = None

    label = _state.get("label")
    if label is not None:
        try:
            if label.winfo_exists():
                label.destroy()
        except Exception:
            pass
        _state["label"] = None


def attach_tooltip(widget, text, delay=0):
    """Show `text` in a small tooltip while the pointer hovers `widget`."""

    def _show(event=None):
        hide_tooltip()
        try:
            top = widget.winfo_toplevel()
            label = ctk.CTkLabel(
                top, text=text, fg_color=theme.PANEL, text_color=theme.TEXT,
                corner_radius=6, padx=8, pady=4, font=theme.FONT_SMALL,
                border_width=1, border_color=theme.BORDER,
            )
        except Exception:
            return
        try:
            x = widget.winfo_rootx() - top.winfo_rootx()
            y = widget.winfo_rooty() - top.winfo_rooty() + widget.winfo_height() + 4
            max_x = max(0, top.winfo_width() - 260)
            x = min(max(0, x), max_x)
            label.place(x=x, y=y)
            label.lift()
        except Exception:
            pass
        _state["label"] = label
        try:
            _state["job"] = (top, top.after(4000, hide_tooltip))
        except Exception:
            _state["job"] = None

    def _hide(event=None):
        hide_tooltip()

    for sequence in ("<Enter>",):
        widget.bind(sequence, _show, add="+")
    for sequence in ("<Leave>", "<ButtonPress>", "<Destroy>", "<Unmap>"):
        widget.bind(sequence, _hide, add="+")
