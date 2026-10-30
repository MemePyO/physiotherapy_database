"""Visual theme constants for the dashboard UI.

The module acts as a palette registry: call ``set_theme(name)`` to switch the
active palette and every ``theme.X`` read afterwards resolves to the new values.
``classic`` is the original look, ``medidash`` matches the MediDashboard Pro
reference design (see ``C:/Users/Admin/Desktop/MediDashboard Code``).
"""
import tkinter.font as _tkfont

# ---- font family selection -------------------------------------------------

def _has_font(name):
    try:
        return name in _tkfont.families()
    except Exception:
        return False


def _inter():
    return "Inter" if _has_font("Inter") else ("Segoe UI" if _has_font("Segoe UI") else "sans-serif")


def _mdl2():
    return "Segoe MDL2 Assets" if _has_font("Segoe MDL2 Assets") else None


def _emoji():
    return "Segoe UI Emoji" if _has_font("Segoe UI Emoji") else "Segoe UI"


# ---- shared sizes ----------------------------------------------------------

_CLASSIC_FONT_TITLE = ("Segoe UI", 18, "bold")
_CLASSIC_FONT_SUB = ("Segoe UI", 12)
_CLASSIC_FONT_BODY = ("Segoe UI", 11)
_CLASSIC_FONT_BOLD = ("Segoe UI", 11, "bold")
_CLASSIC_FONT_SMALL = ("Segoe UI", 10)
_CLASSIC_FONT_SECTION = ("Segoe UI", 12, "bold")

_INTER = _inter()
_MEDIDASH_FONT_TITLE = (_INTER, 22, "bold")
_MEDIDASH_FONT_SUB = (_INTER, 12)
_MEDIDASH_FONT_BODY = (_INTER, 11)
_MEDIDASH_FONT_BOLD = (_INTER, 11, "bold")
_MEDIDASH_FONT_SMALL = (_INTER, 10)
_MEDIDASH_FONT_SECTION = (_INTER, 13, "bold")

_MDL2 = _mdl2()
_EMOJI = _emoji()


# ---- palettes -------------------------------------------------------------

PALETTES = {
    "classic": {
        "BG": "#f4f7fb",
        "PANEL": "#ffffff",
        "BORDER": "#dbe3ec",
        "TEXT": "#1f2d3d",
        "MUTED": "#6b7c8f",
        "ACCENT": "#2f6fb0",
        "ACCENT_DARK": "#1f5f9e",
        "ACCENT_LIGHT": "#e8f1fa",
        "SELECTED": "#dce9f7",
        "DANGER": "#c0392b",
        "SEC_DIAG": "#2f6fb0",
        "SEC_OBJ": "#4a90c2",
        "SEC_EVAL": "#8fb8d8",
        "SEC_OBS": "#9aa7b4",
        "SIDEBAR_BG": "#ffffff",
        "SIDEBAR_ACTIVE": "#e8f1fa",
        "FONT_TITLE": _CLASSIC_FONT_TITLE,
        "FONT_SUB": _CLASSIC_FONT_SUB,
        "FONT_BODY": _CLASSIC_FONT_BODY,
        "FONT_BOLD": _CLASSIC_FONT_BOLD,
        "FONT_SMALL": _CLASSIC_FONT_SMALL,
        "FONT_SECTION": _CLASSIC_FONT_SECTION,
        "ICON_FONT": (_EMOJI, 18),
        "ICON_FONT_SMALL": (_EMOJI, 14),
        "SIDEBAR_W": 72,
        "AVATAR_SIZE": 40,
        "CARD_RADIUS": 10,
        "PANEL_RADIUS": 12,
        "PADDING": 16,
        "RAIL_W": 64,
        "TOPBAR_H": 56,
        "LIST_W": 0,
        "PANE_PAD": 16,
        "BTN_RADIUS": 8,
        "TOPBAR_BG": "#ffffff",
        "RAIL_BG": "#ffffff",
        "INPUT_BG": "#f3f4f6",
        "HEAD_DIAG": "#2f6fb0",
        "HEAD_OBJ": "#4a90c2",
        "HEAD_EVAL": "#8fb8d8",
        "HEAD_OBS": "#9aa7b4",
        "HEAD_TEXT_DARK": False,
        "RIGHT_BG": "#ffffff",
        "ICON_STYLE": "emoji",
    },
    "medidash": {
        "BG": "#f4f7fa",
        "PANEL": "#ffffff",
        "BORDER": "#e3e8ef",
        "TEXT": "#111827",
        "MUTED": "#6b7280",
        "ACCENT": "#2f6fed",
        "ACCENT_DARK": "#1d4ed8",
        "ACCENT_LIGHT": "#dceafe",
        "SELECTED": "#dceafe",
        "DANGER": "#c0392b",
        "SEC_DIAG": "#3b82f6",
        "SEC_OBJ": "#a9d2f0",
        "SEC_EVAL": "#98a2b3",
        "SEC_OBS": "#6b7280",
        "SIDEBAR_BG": "#eaf1f6",
        "SIDEBAR_ACTIVE": "#2f6fed",
        "FONT_TITLE": _MEDIDASH_FONT_TITLE,
        "FONT_SUB": _MEDIDASH_FONT_SUB,
        "FONT_BODY": _MEDIDASH_FONT_BODY,
        "FONT_BOLD": _MEDIDASH_FONT_BOLD,
        "FONT_SMALL": _MEDIDASH_FONT_SMALL,
        "FONT_SECTION": _MEDIDASH_FONT_SECTION,
        "ICON_FONT": ((_MDL2 or _EMOJI), 18),
        "ICON_FONT_SMALL": ((_MDL2 or _EMOJI), 14),
        "SIDEBAR_W": 64,
        "AVATAR_SIZE": 44,
        "CARD_RADIUS": 10,
        "PANEL_RADIUS": 10,
        "PADDING": 24,
        "RAIL_W": 64,
        "TOPBAR_H": 56,
        "LIST_W": 436,
        "PANE_PAD": 26,
        "BTN_RADIUS": 8,
        "TOPBAR_BG": "#ffffff",
        "RAIL_BG": "#eaf1f6",
        "INPUT_BG": "#f3f4f6",
        "HEAD_DIAG": "#3b82f6",
        "HEAD_OBJ": "#a9d2f0",
        "HEAD_EVAL": "#98a2b3",
        "HEAD_OBS": "#6b7280",
        "HEAD_TEXT_DARK": True,
        "RIGHT_BG": "#ffffff",
        "ICON_STYLE": "mdl2" if _MDL2 else "emoji",
    },
}

_active = "classic"


def set_theme(name):
    global _active
    if name not in PALETTES:
        name = "classic"
    _active = name
    _apply(PALETTES[name])


def active():
    return _active


def layout():
    return "stacked" if _active == "medidash" else "tabs"


def _apply(palette):
    globals().update(palette)


# initialise with the classic palette
_apply(PALETTES["classic"])
_active = "classic"

