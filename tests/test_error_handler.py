"""Tests for the crash handler, the in-memory error list and the Diagnostics view."""

import customtkinter as ctk

import log
import main
import utils


def test_recent_errors_capture_warning():
    log.clear_errors()
    logger = log.get_logger("test_error_handler")
    logger.warning("a test warning")
    entries = log.recent_errors()
    assert entries, "warning was not captured"
    assert entries[-1]["level"] == "WARNING"
    assert entries[-1]["message"] == "a test warning"


def test_recent_errors_capture_swallowed_traceback():
    log.clear_errors()
    logger = log.get_logger("test_error_handler")
    try:
        raise ValueError("boom in test")
    except ValueError:
        log.debug_exc(logger)
    entries = log.recent_errors()
    assert entries, "suppressed exception was not captured"
    assert "ValueError: boom in test" in entries[-1]["traceback"]


def test_recent_errors_are_capped_and_redacted():
    log.clear_errors()
    logger = log.get_logger("test_error_handler")
    for i in range(log._RECENT_LIMIT + 7):
        logger.warning("error %d from user@example.com 123456789", i)
    entries = log.recent_errors()
    assert len(entries) == log._RECENT_LIMIT
    assert "user@example.com" not in entries[-1]["message"]
    assert "123456789" not in entries[-1]["message"]
    assert "[redacted]" in entries[-1]["message"]


def test_utils_exists_handles_destroyed_widget(app):
    label = ctk.CTkLabel(app, text="temporary")
    label.destroy()
    assert utils._exists(label) is False
    assert utils._exists(None) is False


def test_callback_exception_is_logged_and_diagnostics_renders(app):
    log.clear_errors()
    main._last_error_dialog = 0.0

    app.report_callback_exception(ValueError, ValueError("callback boom"), None)
    app.update()
    errors = log.recent_errors()
    assert any("callback boom" in (e["message"] + e["traceback"]) for e in errors)

    app._show_view("diagnostics")
    app.update()
    rows = dict(app._health_rows())
    assert main.lang.t("ui_db_integrity") in rows
    assert main.lang.t("ui_patients") in rows
