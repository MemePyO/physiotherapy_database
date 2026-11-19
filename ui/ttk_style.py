"""Themed ttk widget styling.

``ttk`` widgets (Treeview and scrollbars) ignore CustomTkinter colours, so
they are styled from the active palette here.  ``apply(root)`` is idempotent:
widgets created afterwards inherit the style automatically because ttk styles
are shared per Tk interpreter.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import theme

TREEVIEW_STYLE = "Treeview"
HEADING_STYLE = "Treeview.Heading"
SCROLLBAR_STYLE = "TScrollbar"


def apply(root: tk.Misc | None = None) -> ttk.Style:
    """Apply the active palette to ttk widgets and return the style object."""
    style = ttk.Style(master=root) if root is not None else ttk.Style()
    try:
        if style.theme_use() != "clam":
            style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        TREEVIEW_STYLE,
        background=theme.PANEL,
        fieldbackground=theme.PANEL,
        foreground=theme.TEXT,
        bordercolor=theme.BORDER,
        lightcolor=theme.BORDER,
        darkcolor=theme.BORDER,
        borderwidth=0,
        rowheight=theme.TABLE_ROW_H,
    )
    style.map(
        TREEVIEW_STYLE,
        background=[("selected", theme.SELECTED)],
        foreground=[("selected", theme.TEXT)],
    )
    style.configure(
        HEADING_STYLE,
        background=theme.BG,
        foreground=theme.TEXT,
        bordercolor=theme.BORDER,
        lightcolor=theme.BORDER,
        darkcolor=theme.BORDER,
        relief="flat",
        borderwidth=0,
        padding=(6, 4),
        font=theme.FONT_BOLD,
    )
    style.map(HEADING_STYLE, background=[("active", theme.ACCENT_LIGHT)])

    style.configure(
        SCROLLBAR_STYLE,
        background=theme.MUTED,
        troughcolor=theme.BG,
        bordercolor=theme.BORDER,
        arrowcolor=theme.TEXT,
        gripcount=0,
        borderwidth=0,
    )
    style.map(SCROLLBAR_STYLE, background=[("active", theme.ACCENT)])
    for orient in ("Vertical", "Horizontal"):
        style.configure(
            f"{orient}.TScrollbar",
            background=theme.MUTED,
            troughcolor=theme.BG,
            bordercolor=theme.BORDER,
            arrowcolor=theme.TEXT,
            gripcount=0,
            borderwidth=0,
        )
        style.map(f"{orient}.TScrollbar", background=[("active", theme.ACCENT)])
    return style


__all__ = ["apply", "TREEVIEW_STYLE", "HEADING_STYLE", "SCROLLBAR_STYLE"]
