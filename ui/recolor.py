"""Recolour an already-built CustomTkinter widget tree in place.

Switching light/dark never changes the layout, so destroying and rebuilding the
whole window is unnecessary — and is exactly what makes the switch look chunky.
``apply(root, old_palette)`` walks the widget tree and rewrites every colour
option whose current value is an exact colour from the old palette, translating
it to the matching role of the active palette.

Only exact palette colours are touched: ``transparent``, ``auto``, tuples and
any custom hex a caller passed survive untouched.  ``ttk`` widgets are styled
separately through :mod:`ui.ttk_style`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import theme
from ui import ttk_style

# Roles used for text: the same hex can be a surface in one role and a text
# colour in another, so fills and text are translated through separate maps.
TEXT_ROLES = frozenset({"TEXT", "MUTED", "CARD_META", "ON_ACCENT"})

# Deterministic tie-break for old palettes where several roles share one hex.
FILL_PRIORITY = (
    "PANEL",
    "RIGHT_BG",
    "BG",
    "TOPBAR_BG",
    "RAIL_BG",
    "SIDEBAR_BG",
    "INPUT_BG",
    "SELECTED",
    "ACCENT_LIGHT",
    "ACCENT",
    "ACCENT_DARK",
    "SIDEBAR_ACTIVE",
    "BORDER",
    "DANGER",
    "DANGER_HOVER",
    "MUTED_BTN",
    "MUTED_BTN_HOVER",
    "SEC_DIAG",
    "SEC_OBJ",
    "SEC_EVAL",
    "SEC_OBS",
    "HEAD_DIAG",
    "HEAD_OBJ",
    "HEAD_EVAL",
    "HEAD_OBS",
)
TEXT_PRIORITY = ("TEXT", "ON_ACCENT", "CARD_META", "MUTED")

FILL_PROPS = (
    "fg_color",
    "bg_color",
    "border_color",
    "hover_color",
    "button_color",
    "button_hover_color",
    "progress_color",
    "selected_color",
    "selected_hover_color",
    "unselected_color",
    "unselected_hover_color",
    "dropdown_fg_color",
    "dropdown_hover_color",
    "scrollbar_button_color",
    "scrollbar_button_hover_color",
    "checkmark_color",
)
TEXT_PROPS = ("text_color", "placeholder_text_color", "dropdown_text_color")
ALL_PROPS = FILL_PROPS + TEXT_PROPS

# Probing an unsupported option raises in Tk, so remember the answer per class.
_SUPPORTED: dict[type, tuple[str, ...]] = {}


def snapshot(palette: Mapping[str, object] | None = None) -> dict[str, str]:
    """Return just the colour roles of a palette (the active one by default)."""
    if palette is None:
        palette = theme.PALETTES[theme.active()]
    colours: dict[str, str] = {}
    for role, value in palette.items():
        if isinstance(value, str) and value.startswith("#"):
            colours[role] = value
    return colours


def _ordered_roles(names: Iterable[str], priority: Iterable[str]) -> tuple[str, ...]:
    available = tuple(names)
    ordered = [name for name in priority if name in available]
    ordered.extend(name for name in available if name not in ordered)
    return tuple(ordered)


def _build_map(
    old: Mapping[str, str],
    new: Mapping[str, str],
    roles: Iterable[str],
) -> dict[str, str]:
    """Map old hex -> new hex, first role in ``roles`` winning any collision."""
    mapping: dict[str, str] = {}
    for role in roles:
        old_value = old.get(role)
        new_value = new.get(role)
        if not old_value or not new_value:
            continue
        mapping.setdefault(old_value.lower(), new_value)
    return mapping


def build_maps(
    old: Mapping[str, str], new: Mapping[str, str]
) -> tuple[dict[str, str], dict[str, str]]:
    """Return ``(fill_map, text_map)`` for the two role classes."""
    names = tuple(role for role in old if role in new)
    fill_roles = _ordered_roles((role for role in names if role not in TEXT_ROLES), FILL_PRIORITY)
    text_roles = _ordered_roles((role for role in names if role in TEXT_ROLES), TEXT_PRIORITY)
    return (
        _build_map(old, new, fill_roles),
        _build_map(old, new, text_roles),
    )


def _supported(widget: object) -> tuple[str, ...]:
    cls = type(widget)
    cached = _SUPPORTED.get(cls)
    if cached is not None:
        return cached
    supported: list[str] = []
    for prop in ALL_PROPS:
        try:
            widget.cget(prop)  # type: ignore[attr-defined]
        except Exception:
            continue
        supported.append(prop)
    _SUPPORTED[cls] = tuple(supported)
    return _SUPPORTED[cls]


def _translate(value: object, mapping: Mapping[str, str]) -> object:
    if not isinstance(value, str):
        return value
    return mapping.get(value.strip().lower(), value)


def _recolour_option(widget: object, prop: str, mapping: Mapping[str, str]) -> int:
    try:
        current = widget.cget(prop)  # type: ignore[attr-defined]
    except Exception:
        return 0
    new_value = _translate(current, mapping)
    if new_value == current:
        return 0
    try:
        widget.configure(**{prop: new_value})  # type: ignore[attr-defined]
    except Exception:
        return 0
    return 1


def recolour_tree(
    widget: object,
    fill_map: Mapping[str, str],
    text_map: Mapping[str, str],
) -> int:
    """Rewrite palette colours in ``widget`` and its descendants."""
    changed = 0
    supported = _supported(widget)
    for prop in supported:
        mapping = text_map if prop in TEXT_PROPS else fill_map
        changed += _recolour_option(widget, prop, mapping)
    try:
        children = widget.winfo_children()  # type: ignore[attr-defined]
    except Exception:
        return changed
    for child in children:
        changed += recolour_tree(child, fill_map, text_map)
    return changed


def apply(root: object, old: Mapping[str, str], new: Mapping[str, str] | None = None) -> int:
    """Recolour ``root`` from ``old`` to the active palette and restyle ttk.

    Returns the number of widget options that changed; never raises.
    """
    try:
        if new is None:
            new = snapshot()
        fill_map, text_map = build_maps(old, new)
        changed = recolour_tree(root, fill_map, text_map)
        try:
            scale = None
            getter = getattr(root, "current_ui_scale", None)
            if callable(getter):
                scale = getter()
            ttk_style.apply(root, scale=scale)  # type: ignore[arg-type]
        except Exception:
            pass
        return changed
    except Exception:
        return 0


__all__ = [
    "ALL_PROPS",
    "FILL_PROPS",
    "TEXT_PROPS",
    "apply",
    "build_maps",
    "recolour_tree",
    "snapshot",
]
