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

def _modern():
    if _has_font("Bahnschrift"):
        return "Bahnschrift"
    if _has_font("Segoe UI Semibold"):
        return "Segoe UI Semibold"
    return _inter()


_INTER = _inter()
_MODERN = _modern()
_MEDIDASH_FONT_TITLE = (_MODERN, 22, "bold")
_MEDIDASH_FONT_SUB = (_MODERN, 12)
_MEDIDASH_FONT_BODY = (_MODERN, 11)
_MEDIDASH_FONT_BOLD = (_MODERN, 11, "bold")
_MEDIDASH_FONT_SMALL = (_MODERN, 10)
_MEDIDASH_FONT_SECTION = (_MODERN, 13, "bold")

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
        "CARD_META": "#4b5563",
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
        "ICON_FONT": (_EMOJI, 22),
        "ICON_FONT_SMALL": (_EMOJI, 18),
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
        "CARD_META": "#4b5563",
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
        "ICON_FONT": ((_MDL2 or _EMOJI), 22),
        "ICON_FONT_SMALL": ((_MDL2 or _EMOJI), 18),
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
    "medidash-dark": {
        "BG": "#0f172a",
        "PANEL": "#1f2937",
        "BORDER": "#374151",
        "TEXT": "#f9fafb",
        "MUTED": "#9ca3af",
        "CARD_META": "#d1d5db",
        "ACCENT": "#2f6fed",
        "ACCENT_DARK": "#1d4ed8",
        "ACCENT_LIGHT": "#1e3a8a",
        "SELECTED": "#1e3a5f",
        "DANGER": "#ef4444",
        "SEC_DIAG": "#2563eb",
        "SEC_OBJ": "#3b82f6",
        "SEC_EVAL": "#6b7280",
        "SEC_OBS": "#4b5563",
        "SIDEBAR_BG": "#111827",
        "SIDEBAR_ACTIVE": "#2f6fed",
        "FONT_TITLE": _MEDIDASH_FONT_TITLE,
        "FONT_SUB": _MEDIDASH_FONT_SUB,
        "FONT_BODY": _MEDIDASH_FONT_BODY,
        "FONT_BOLD": _MEDIDASH_FONT_BOLD,
        "FONT_SMALL": _MEDIDASH_FONT_SMALL,
        "FONT_SECTION": _MEDIDASH_FONT_SECTION,
        "ICON_FONT": ((_MDL2 or _EMOJI), 22),
        "ICON_FONT_SMALL": ((_MDL2 or _EMOJI), 18),
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
        "TOPBAR_BG": "#1f2937",
        "RAIL_BG": "#111827",
        "INPUT_BG": "#374151",
        "HEAD_DIAG": "#2563eb",
        "HEAD_OBJ": "#3b82f6",
        "HEAD_EVAL": "#6b7280",
        "HEAD_OBS": "#4b5563",
        "HEAD_TEXT_DARK": False,
        "RIGHT_BG": "#1f2937",
        "ICON_STYLE": "mdl2" if _MDL2 else "emoji",
    },
}

_base = "classic"
_appearance = "Light"
_active = "classic"


def _resolve_name():
    if _base == "medidash" and _appearance == "Dark" and "medidash-dark" in PALETTES:
        return "medidash-dark"
    return _base


def set_theme(name):
    global _base, _active
    if name not in ("classic", "medidash"):
        name = "classic"
    _base = name
    _active = _resolve_name()
    _apply(PALETTES[_active])


def set_appearance(mode):
    global _appearance, _active
    _appearance = "Dark" if str(mode).lower().startswith("d") else "Light"
    _active = _resolve_name()
    _apply(PALETTES[_active])


def base():
    return _base


def appearance():
    return _appearance


def active():
    return _active


def layout():
    return "stacked" if _active.startswith("medidash") else "tabs"


def _apply(palette):
    globals().update(palette)


# initialise with the classic palette (light)
_apply(PALETTES["classic"])
_active = "classic"
_base = "classic"
_appearance = "Light"

