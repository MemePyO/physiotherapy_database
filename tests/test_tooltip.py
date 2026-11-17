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
