import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import theme


def test_palettes_have_same_keys():
    assert set(theme.PALETTES["classic"].keys()) == set(theme.PALETTES["medidash"].keys())


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
    assert theme.active() == "classic"


def test_required_keys_present():
    required = ["BG", "PANEL", "BORDER", "TEXT", "MUTED", "ACCENT", "ACCENT_DARK",
                "SELECTED", "DANGER", "FONT_TITLE", "FONT_BODY", "ICON_FONT",
                "SIDEBAR_W", "AVATAR_SIZE", "CARD_RADIUS", "PADDING"]
    for name in ("classic", "medidash"):
        for k in required:
            assert k in theme.PALETTES[name], (name, k)


def test_icon_font_is_tuple():
    for name in ("classic", "medidash"):
        theme.set_theme(name)
        assert isinstance(theme.ICON_FONT, tuple)
    theme.set_theme("classic")