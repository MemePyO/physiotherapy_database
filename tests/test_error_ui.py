"""Tests for the centralized error presentation helper."""

import tkinter.messagebox as messagebox

import error_ui


def test_report_error_shows_standard_dialog(monkeypatch):
    calls = []
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: calls.append((a, k)))
    error_ui.report_error("boom")
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[1] == "boom"
    assert "parent" not in kwargs


def test_report_error_forwards_owner(monkeypatch):
    calls = []
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: calls.append((a, k)))
    owner = object()
    error_ui.report_error("boom", owner=owner)
    assert calls[0][1]["parent"] is owner


def test_report_error_swallows_dialog_failures(monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("no display")

    monkeypatch.setattr(messagebox, "showerror", explode)
    # Must not propagate: error presentation is best-effort.
    error_ui.report_error("boom")
