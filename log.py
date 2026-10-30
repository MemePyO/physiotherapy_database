"""Centralized logging configuration (rotating file + console)."""
import logging
import os
import re
from logging.handlers import RotatingFileHandler

_CONFIGURED = False

# Patterns that may contain PII or secrets; redacted in all log output.
_REDACT_PATTERNS = [
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),          # emails
    re.compile(r"\b\d{6,}\b"),                              # long numeric IDs/phones
]


class _RedactFilter(logging.Filter):
    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return True
        for pat in _REDACT_PATTERNS:
            msg = pat.sub("[redacted]", msg)
        record.msg = msg
        record.args = ()
        return True


def setup():
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True
    base = os.path.dirname(os.path.abspath(__file__))
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


def get_logger(name):
    setup()
    return logging.getLogger(name)
