"""Centralized logging configuration (rotating file + console)."""
import logging
import os
from logging.handlers import RotatingFileHandler

_CONFIGURED = False


def setup():
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True
    base = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base, "app.log")
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    try:
        fh = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        root.addHandler(fh)
    except Exception:
        pass
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(logging.WARNING)
    root.addHandler(ch)


def get_logger(name):
    setup()
    return logging.getLogger(name)
