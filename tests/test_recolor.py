from tkinter import ttk

import customtkinter as ctk
import pytest

import theme
from ui import recolor


def _probe(app):
    frame = ctk.CTkFrame(app, fg_color=theme.PANEL, border_color=theme.BORDER, border_width=1)
    label = ctk.CTkLabel(frame, text="probe", text_color=theme.TEXT)
    label.pack()
    # The App window is managed by grid, so use place for the probe.
    frame.place(x=0, y=0)
    app.update_idletasks()
    return frame, label


def test_snapshot_only_returns_colours():
    palette = recolor.snapshot(theme.PALETTES["classic"])
    assert palette["PANEL"] == theme.PALETTES["classic"]["PANEL"]
    assert "FONT_BODY" not in palette
    assert "SIDEBAR_W" not in palette


def test_build_maps_separates_text_and_fill_roles():
    old = {"PANEL": "#ffffff", "ON_ACCENT": "#ffffff", "TEXT": "#000000"}
    new = {"PANEL": "#111111", "ON_ACCENT": "#ffffff", "TEXT": "#eeeeee"}
    fill_map, text_map = recolor.build_maps(old, new)
    # White is a surface for fills but stays white as text.
    assert fill_map["#ffffff"] == "#111111"
    assert text_map["#ffffff"] == "#ffffff"
    assert text_map["#000000"] == "#eeeeee"
    assert "#000000" not in fill_map


def test_recolour_translates_palette_colours(patient_app):
    app, _pid = patient_app
    frame, label = _probe(app)
    before = theme.PANEL
    app._apply_appearance("Dark")
    app.update()
    assert theme.active() == "classic-dark"
    # Same widget objects: recoloured in place, not rebuilt.
    assert frame.winfo_exists()
    assert frame.cget("fg_color") == theme.PANEL
    assert frame.cget("fg_color") != before
    assert frame.cget("border_color") == theme.BORDER
    assert label.cget("text_color") == theme.TEXT


def test_recolour_preserves_custom_and_transparent_colours(patient_app):
    app, _pid = patient_app
    custom = ctk.CTkFrame(app, fg_color="#123456", border_color="#abcdef", border_width=1)
    transparent = ctk.CTkFrame(app, fg_color="transparent")
    custom.place(x=0, y=0)
    transparent.place(x=70, y=0)
    app.update_idletasks()
    app._apply_appearance("Dark")
    app.update()
    assert custom.cget("fg_color") == "#123456"
    assert custom.cget("border_color") == "#abcdef"
    assert transparent.cget("fg_color") == "transparent"


def test_toggle_theme_recolours_without_rebuilding(patient_app, monkeypatch):
    app, _pid = patient_app
    rebuilt = []
    monkeypatch.setattr(app, "_rebuild_ui", lambda: rebuilt.append(True))
    app._toggle_theme()
    assert theme.active() == "classic-dark"
    assert rebuilt == []
    app._toggle_theme()
    assert theme.active() == "classic"
    assert rebuilt == []


def test_recolour_restyles_ttk(patient_app):
    app, _pid = patient_app
    app._apply_appearance("Dark")
    app.update()
    style = ttk.Style(master=app)
    assert style.lookup("Treeview", "background").lower() == theme.PANEL.lower()
    assert style.lookup("Treeview.Heading", "foreground").lower() == theme.TEXT.lower()


@pytest.mark.parametrize("base", ["classic", "medidash"])
def test_both_bases_have_dark_palettes(base):
    theme.set_theme(base)
    theme.set_appearance("Dark")
    assert theme.active() == base + "-dark"
    theme.set_appearance("Light")
    assert theme.active() == base
    theme.set_theme("classic")
