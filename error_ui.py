"""Single entry point for user-facing error dialogs.

Keeping the presentation in one place means every caught error looks the same
and a future move to a status bar or toast only needs one change.
"""

import tkinter.messagebox as messagebox

import lang
import log

logger = log.get_logger(__name__)


def report_error(message, owner=None):
    """Show *message* in the standard error dialog, never raising."""
    text = str(message)
    try:
        if owner is not None:
            messagebox.showerror(lang.t("app_name"), text, parent=owner)
        else:
            messagebox.showerror(lang.t("app_name"), text)
    except Exception:
        log.debug_exc(logger)
