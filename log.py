"""Centralized logging configuration (rotating file + console + recent-errors list).

Besides writing ``app.log``, this module keeps the last few warnings/errors in
memory so the Diagnostics view can show them without asking the user to read
the log file.  Swallowed exceptions logged through ``debug_exc`` are captured
too — they are exactly the ones that used to disappear silently.
"""
import collections
import datetime
import logging
import os
import re
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler

_CONFIGURED = False
_RECENT_LIMIT = 50

# The most recent warnings/errors, newest last.  Guarded by _recent_lock
# because Tk callbacks and background threads can log at the same time.
_recent = collections.deque(maxlen=_RECENT_LIMIT)
_recent_lock = threading.Lock()


def _base_dir() -> str:
    try:
        import paths
        return paths.app_data_dir()
    except Exception:
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))


# Patterns that may contain PII or secrets; redacted in all log output.
_REDACT_PATTERNS = [
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),          # emails
    re.compile(r"\b\d{6,}\b"),                              # long numeric IDs/phones
]


def _redact(text):
    """Hide e-mails and long numbers before text is written anywhere."""
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub("[redacted]", text)
    return text


class _RedactFilter(logging.Filter):
    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return True
        record.msg = _redact(msg)
        record.args = ()
        return True


def _remember(level, logger_name, message, trace_text=""):
    """Add one entry to the in-memory list used by the Diagnostics view."""
    entry = {
        "time": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "level": level,
        "logger": logger_name,
        "message": _redact(message),
        "traceback": _redact(trace_text),
    }
    with _recent_lock:
        _recent.append(entry)


def recent_errors():
    """Return a copy of the captured warnings/errors (newest last)."""
    with _recent_lock:
        return list(_recent)


def clear_errors():
    """Empty the in-memory error list (the log file is left untouched)."""
    with _recent_lock:
        _recent.clear()


class _RecentErrorsHandler(logging.Handler):
    """Keep warnings, errors and swallowed tracebacks for the Diagnostics view."""

    def emit(self, record):
        try:
            message = record.getMessage()
            is_suppressed = "suppressed exception" in message
            if record.levelno < logging.WARNING and not is_suppressed:
                return

            trace_text = ""
            if record.exc_info and record.exc_info[0] is not None:
                trace_text = "".join(traceback.format_exception(*record.exc_info))
            elif is_suppressed:
                # debug_exc() writes the traceback straight into the message.
                _, _, trace_text = message.partition("suppressed exception:")
                trace_text = trace_text.strip()
                message = "suppressed exception"

            _remember(record.levelname, record.name, message, trace_text)
        except Exception:
            # The error logger must never become a source of errors itself.
            pass


def setup():
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True
    base = _base_dir()
    log_path = os.path.join(base, "app.log")
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    redactor = _RedactFilter()
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    try:
        fh = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        fh.addFilter(redactor)
        root.addHandler(fh)
    except Exception:
        pass
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.WARNING)
    ch.addFilter(redactor)
    root.addHandler(ch)
    # Keep the newest warnings/errors in memory for the Diagnostics view.
    recent = _RecentErrorsHandler()
    recent.setLevel(logging.DEBUG)
    root.addHandler(recent)


def get_logger(name):
    setup()
    return logging.getLogger(name)


def debug_exc(logger):
    """Log the exception currently being handled, with traceback, at DEBUG."""
    logger.debug("suppressed exception:\n%s", traceback.format_exc())
