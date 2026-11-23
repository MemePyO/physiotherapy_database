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


def scaled_font(font, scale):
    """Return a Tk font tuple with its point size multiplied by *scale*."""
    if not font or scale == 1.0:
        return font
    try:
        family = font[0]
        size = int(float(font[1]) * scale + 0.5)
        style = tuple(font[2:])
        return (family, max(6, size)) + style
    except Exception:
        return font


def apply(root: tk.Misc | None = None, scale: float | None = None) -> ttk.Style:
    """Apply the active palette to ttk widgets and return the style object.

    ``scale`` follows the user's interface scale (1.0 / 1.25 / 1.5).  Plain
    ``ttk`` widgets are not touched by CustomTkinter's widget scaling, so row
    height and fonts are scaled here to stay in step with the CTk widgets.
    """
    try:
        scale = float(scale) if scale else 1.0
    except (TypeError, ValueError):
        scale = 1.0
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
        rowheight=max(12, int(theme.TABLE_ROW_H * scale + 0.5)),
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
        font=scaled_font(theme.FONT_BOLD, scale),
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


__all__ = ["apply", "scaled_font", "TREEVIEW_STYLE", "HEADING_STYLE", "SCROLLBAR_STYLE"]
