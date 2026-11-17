"""Interaction tests for the themed dialogs (non-blocking variants)."""

import pytest


@pytest.fixture
def non_blocking(monkeypatch):
    from dialogs import base_dialog

    monkeypatch.setattr(base_dialog.BaseDialog, "wait_window", lambda self, window: None)


def test_input_dialog_variants(app, non_blocking, monkeypatch):
    from dialogs import input_dialog
    from dialogs.input_dialog import CTkInputDialog

    dlg = CTkInputDialog(app, "Title", "Prompt", initialvalue="initial")
    assert dlg.entry.get() == "initial"
    dlg._ok()
    assert dlg.get_input() == "initial"

    dlg = CTkInputDialog(
        app, "Title", "Prompt", validate=lambda value: "required" if not value else None
    )
    dlg.entry.delete(0, "end")
    dlg._ok()
    assert dlg.get_input() is None
    assert dlg.err_label.cget("text") == "required"
    dlg.entry.insert(0, "valid")
    dlg._ok()
    assert dlg.get_input() == "valid"

    dlg = CTkInputDialog(app, "Title", "Prompt")
    dlg._cancel()
    assert dlg.get_input() is None

    class _Stub:
        def __init__(self, *args, **kwargs):
            self.value = "typed"

        def get_input(self):
            return self.value

    monkeypatch.setattr(input_dialog, "CTkInputDialog", _Stub)
    assert input_dialog.ask_string(app, "t", "p") == "typed"


def test_confirmation_base_and_save_as(app, non_blocking, monkeypatch):
    from dialogs import SaveAsDialog, confirmation_dialog
    from dialogs.base_dialog import BaseDialog
    from dialogs.confirmation_dialog import CTkConfirmationDialog

    dlg = CTkConfirmationDialog(app, "Confirm", "Continue?")
    dlg._yes()
    assert dlg.get_result() is True
    dlg = CTkConfirmationDialog(app, "Confirm", "Continue?")
    dlg._no()
    assert dlg.get_result() is False

    class _Stub:
        def __init__(self, *args, **kwargs):
            pass

        def get_result(self):
            return True

    monkeypatch.setattr(confirmation_dialog, "CTkConfirmationDialog", _Stub)
    assert confirmation_dialog.ask_yes_no(app, "t", "m") is True

    base = BaseDialog(app, "Base", width=300, height=150)
    assert base._add_buttons(ok_text="Go", cancel_text="Stop") is not None
    base.destroy()
    plain = BaseDialog(app, "Base")
    assert plain._add_buttons(ok_text="", cancel_text="") is not None
    plain.destroy()

    save_as = SaveAsDialog(app)
    app.update()
    assert save_as.result is None
    save_as.fmt.set("pdf")
    save_as._ok()
    assert save_as.result == "pdf"
