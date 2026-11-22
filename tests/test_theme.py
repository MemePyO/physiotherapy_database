import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import theme


@pytest.fixture(autouse=True)
def _reset_theme():
    """Keep palette state deterministic regardless of test order."""
    theme.set_theme("classic")
    theme.set_appearance("Light")
    yield
    theme.set_theme("medidash")
    theme.set_appearance("Light")


def test_palettes_have_same_keys():
    names = ("classic", "classic-dark", "medidash", "medidash-dark")
    reference = set(theme.PALETTES["classic"].keys())
    for name in names:
        assert set(theme.PALETTES[name].keys()) == reference, name


def test_set_theme_switches():
    theme.set_theme("classic")
    assert theme.active() == "classic"
    assert theme.layout() == "tabs"
    classic_accent = theme.ACCENT
    theme.set_theme("medidash")
    assert theme.active() == "medidash"
    assert theme.layout() == "stacked"
    assert theme.ACCENT != classic_accent
    theme.set_theme("classic")


def test_unknown_theme_falls_back():
    theme.set_theme("nope")
    assert theme.active() == "medidash"


def test_classic_dark_palette_resolves():
    theme.set_theme("classic")
    theme.set_appearance("Dark")
    assert theme.active() == "classic-dark"
    assert theme.layout() == "tabs"
    assert theme.TEXT != theme.PALETTES["classic"]["TEXT"]
    assert theme.PANEL != theme.PALETTES["classic"]["PANEL"]
    theme.set_appearance("Light")
    assert theme.active() == "classic"


def test_medidash_dark_palette_resolves():
    theme.set_theme("medidash")
    theme.set_appearance("Dark")
    assert theme.active() == "medidash-dark"
    assert theme.layout() == "stacked"
    theme.set_appearance("Light")
    assert theme.active() == "medidash"


def test_required_keys_present():
    required = [
        "BG",
        "PANEL",
        "BORDER",
        "TEXT",
        "MUTED",
        "ACCENT",
        "ACCENT_DARK",
        "SELECTED",
        "DANGER",
        "FONT_TITLE",
        "FONT_BODY",
        "ICON_FONT",
        "SIDEBAR_W",
        "AVATAR_SIZE",
        "CARD_RADIUS",
        "PADDING",
    ]
    for name in ("classic", "classic-dark", "medidash", "medidash-dark"):
        for k in required:
            assert k in theme.PALETTES[name], (name, k)


def test_icon_font_is_tuple():
    for name in ("classic", "classic-dark", "medidash", "medidash-dark"):
        assert isinstance(theme.PALETTES[name]["ICON_FONT"], tuple)
    theme.set_theme("classic")
