"""Shared helpers for dialog modules."""

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

import lang
import log
import theme
import utils
from utils import _validate_dob

LANG_LABELS = {"en": "English", "ro": "Rom\u00e2n\u0103"}
logger = log.get_logger(__name__)


def dialog_scale(master) -> float:
    """Return the app's interface scale, falling back to 1.0."""
    try:
        return float(master.current_ui_scale())
    except Exception:
        return 1.0


def fit_to_content(dialog, min_width: int, min_height: int) -> None:
    """Grow a dialog to at least its requested size (never shrink below min).

    CustomTkinter scales ``geometry()`` requests by the window scaling factor,
    while ``winfo_reqheight()`` already reports physical pixels, so the
    requested size is divided by that factor before it is re-applied.
    """
    try:
        if not dialog.winfo_exists():
            return
        dialog.update_idletasks()
        from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker

        scale = float(ScalingTracker.get_window_scaling(dialog)) or 1.0
        width = max(int(min_width), int(round(dialog.winfo_reqwidth() / scale)))
        height = max(int(min_height), int(round(dialog.winfo_reqheight() / scale)))
        # A plain geometry() call is ignored once a CTk toplevel is mapped, so
        # re-show the window after applying the new size.
        dialog.withdraw()
        try:
            dialog.geometry(f"{width}x{height}")
        finally:
            dialog.deiconify()
        dialog.update_idletasks()
        try:
            master = dialog.master
            actual_w = dialog.winfo_width()
            actual_h = dialog.winfo_height()
            x = master.winfo_rootx() + (master.winfo_width() - actual_w) // 2
            y = master.winfo_rooty() + (master.winfo_height() - actual_h) // 2
            dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass
    except Exception:
        logger.debug("could not fit dialog to its content", exc_info=True)


__all__ = [
    "tk",
    "messagebox",
    "ttk",
    "ctk",
    "lang",
    "log",
    "theme",
    "utils",
    "_validate_dob",
    "LANG_LABELS",
    "logger",
    "dialog_scale",
    "fit_to_content",
]
