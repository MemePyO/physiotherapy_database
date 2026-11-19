"""Tests for the in-window hover tooltip lifecycle."""

import tkinter as tk

import customtkinter as ctk

import tooltip


def test_tooltip_lifecycle(app):
    win = ctk.CTkToplevel(app)
    widget = tk.Button(win, text="hover me")
    widget.pack()
    win.update()
    handlers = {}
    widget.bind = lambda sequence, func, add=None: handlers.__setitem__(sequence, func)

    tooltip.attach_tooltip(widget, "helpful text")
    assert set(handlers) == {"<Enter>", "<Leave>", "<ButtonPress>", "<Destroy>", "<Unmap>"}

    handlers["<Enter>"]()
    app.update()
    assert tooltip._state["label"] is not None

    handlers["<Leave>"]()
    app.update()
    assert tooltip._state["label"] is None

    # cancelling a pending auto-hide job and destroying its label
    calls = []

    class _Job:
        def after_cancel(self, job_id):
            calls.append(job_id)

    class _Label:
        def winfo_exists(self):
            return True

        def destroy(self):
            calls.append("destroyed")

    tooltip._state["job"] = (_Job(), "job-1")
    tooltip._state["label"] = _Label()
    tooltip.hide_tooltip()
    assert calls == ["job-1", "destroyed"]
    assert tooltip._state["job"] is None
    assert tooltip._state["label"] is None

    # hiding without any state is safe
    tooltip.hide_tooltip()
    win.destroy()


def test_tooltip_state_is_per_toplevel(app):
    win_a = ctk.CTkToplevel(app)
    win_b = ctk.CTkToplevel(app)
    widget_a = tk.Button(win_a, text="a")
    widget_a.pack()
    widget_b = tk.Button(win_b, text="b")
    widget_b.pack()
    win_a.update()
    win_b.update()

    handlers_a = {}
    handlers_b = {}
    widget_a.bind = lambda sequence, func, add=None: handlers_a.__setitem__(sequence, func)
    widget_b.bind = lambda sequence, func, add=None: handlers_b.__setitem__(sequence, func)
    tooltip.attach_tooltip(widget_a, "text a")
    tooltip.attach_tooltip(widget_b, "text b")

    handlers_a["<Enter>"]()
    app.update()
    label_a = tooltip._state["label"]
    assert label_a is not None

    handlers_b["<Enter>"]()
    app.update()
    assert not label_a.winfo_exists()
    label_b = tooltip._state["label"]
    assert label_b is not None

    # hiding window A must leave window B's tooltip alone
    tooltip.hide_tooltip(win_a)
    assert tooltip._state["label"] is label_b

    tooltip.hide_tooltip(win_b)
    assert tooltip._state["label"] is None
    win_a.destroy()
    win_b.destroy()
