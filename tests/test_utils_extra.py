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
