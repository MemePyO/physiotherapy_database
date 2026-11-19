"""Single, in-window hover tooltips.

Only one tooltip is visible at a time per top-level window, and it is a label
placed inside that window instead of a separate top-level window, so it can
never be left behind on the desktop when the pointer moves away quickly.
State is kept per toplevel so a dialog and the main window never cancel each
other's timers.
"""

import tkinter as tk
import typing as t

import customtkinter as ctk

import theme


class _TooltipState(t.TypedDict):
    label: ctk.CTkLabel | None
    job: tuple[tk.Misc, str] | None


def _empty_state() -> _TooltipState:
    return {"label": None, "job": None}


_states: dict[str, _TooltipState] = {}
# Backwards-compatible handle for tests and callers: the most recent state.
_state: _TooltipState = _empty_state()


def _state_for(window: tk.Misc) -> _TooltipState:
    try:
        key = str(window)
    except Exception:
        key = ""
    state = _states.get(key)
    if state is None:
        state = _empty_state()
        _states[key] = state
    return state


def _clear_state(state: _TooltipState) -> None:
    job = state.get("job")
    if job is not None:
        window, job_id = job
        try:
            window.after_cancel(job_id)
        except Exception:
            pass
        state["job"] = None

    label = state.get("label")
    if label is not None:
        try:
            if label.winfo_exists():
                label.destroy()
        except Exception:
            pass
        state["label"] = None


def hide_tooltip(window: tk.Misc | None = None) -> None:
    """Remove visible tooltips and cancel their auto-hide timers.

    Without *window* every known toplevel is cleared, which is what the app
    uses on global events (click, unmap).  Passing a window only clears that
    window's tooltip, so dialogs stay independent.
    """
    if window is None:
        targets = list(_states.values())
        if all(target is not _state for target in targets):
            targets.append(_state)
    else:
        targets = [_state_for(window)]
    for state in targets:
        _clear_state(state)


def attach_tooltip(widget: tk.Misc, text: str, delay: int = 0) -> None:
    """Show `text` in a small tooltip while the pointer hovers `widget`."""

    def _show(event=None):
        hide_tooltip()
        try:
            top = widget.winfo_toplevel()
            label = ctk.CTkLabel(
                top,
                text=text,
                fg_color=theme.PANEL,
                text_color=theme.TEXT,
                corner_radius=6,
                padx=8,
                pady=4,
                font=theme.FONT_SMALL,
                border_width=1,
                border_color=theme.BORDER,
            )
        except Exception:
            return
        state = _state_for(top)
        global _state
        _state = state
        try:
            x = widget.winfo_rootx() - top.winfo_rootx()
            y = widget.winfo_rooty() - top.winfo_rooty() + widget.winfo_height() + 4
            max_x = max(0, top.winfo_width() - 260)
            x = min(max(0, x), max_x)
            label.place(x=x, y=y)
            label.lift()
        except Exception:
            pass
        state["label"] = label
        try:
            state["job"] = (top, top.after(4000, lambda: hide_tooltip(top)))
        except Exception:
            state["job"] = None

    def _hide(event=None):
        try:
            hide_tooltip(widget.winfo_toplevel())
        except Exception:
            hide_tooltip()

    for sequence in ("<Enter>",):
        widget.bind(sequence, _show, add="+")
    for sequence in ("<Leave>", "<ButtonPress>", "<Destroy>", "<Unmap>"):
        widget.bind(sequence, _hide, add="+")
