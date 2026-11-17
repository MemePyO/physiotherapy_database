import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk

import customtkinter as ctk

from utils import _apply_inline_formatting, _norm, _strip_inline_formatting


def test_strip_inline():
    assert _strip_inline_formatting("a **b** c *d*") == "a b c d"
    assert _strip_inline_formatting(None) is None
    assert _strip_inline_formatting("") == ""
    assert _strip_inline_formatting("plain") == "plain"


def test_apply_inline_formatting_tags():
    root = tk.Tk()
    root.withdraw()
    txt = ctk.CTkTextbox(root)
    txt.pack()
    txt.insert("1.0", "Hello **bold** and *italic*")
    _apply_inline_formatting(txt)
    tb = txt._textbox
    assert tb.tag_ranges("md_bold")
    assert tb.tag_ranges("md_italic")
    assert tb.tag_ranges("md_marker")
    # raw text unchanged
    assert txt.get("1.0", "end-1c") == "Hello **bold** and *italic*"
    root.destroy()


def test_norm_still_works():
    assert _norm("Ștefan") == "stefan"


def test_initials_variants():
    import utils

    assert utils._initials("") == "?"
    assert utils._initials("Ana") == "AN"
    assert utils._initials("Ana Maria Pop") == "AP"


def test_validate_dob_variants():
    import utils

    assert utils._validate_dob("") is True
    assert utils._validate_dob("  ") is True
    assert utils._validate_dob("12.05.1990") is True
    assert utils._validate_dob("1990-05-12") is False


def test_rtf_escape_and_pdf_generation():
    import utils

    assert utils._rtf_escape(r"a\b{c}") == r"a\\b\{c\}"
    data = utils._make_simple_pdf("Patient (1)\nline two")
    assert data.startswith(b"%PDF-1.4")
    assert data.endswith(b"%%EOF\n")


def test_safe_widget_helpers_handle_destroyed_widgets():
    import utils

    root = tk.Tk()
    root.withdraw()
    widget = ctk.CTkButton(root, text="x")
    assert utils._exists(widget) is True
    utils._safe_after(widget, 0, lambda: None)
    utils._safe_format(widget)
    utils._safe_configure(widget, text="y")
    widget.destroy()
    assert utils._exists(widget) is False
    # all helpers must be no-ops after destruction rather than raising
    utils._safe_destroy(widget)
    utils._safe_configure(widget, text="z")
    utils._safe_format(widget)
    assert utils._safe_after(widget, 0, lambda: None) is None
    root.destroy()


def test_patch_scrollable_tolerates_missing_canvas():
    import utils

    class _Frame:
        def __init__(self):
            self.handler = None

        def bind(self, sequence, handler):
            self.handler = handler

    frame = _Frame()
    utils._patch_scrollable(frame)
    frame.handler()  # no _parent_canvas -> returns quietly
