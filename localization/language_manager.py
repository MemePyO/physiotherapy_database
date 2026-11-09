"""Language manager: loads strings from JSON files with fallback to lang.py."""

import json
import os
import sys

_CURRENT = "en"
_STRINGS = {}
_MISSING = set()
_FALLBACK = {}


def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _load_json(lang_code):
    path = os.path.join(_base_dir(), "localization", lang_code + ".json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def load_fallback():
    """Load the legacy lang.STRINGS as fallback."""
    global _FALLBACK
    try:
        sys.path.insert(0, _base_dir())
        import lang

        _FALLBACK = {}
        for key, val in lang.STRINGS.items():
            _FALLBACK[key] = val.get("en", key)
    except Exception:
        _FALLBACK = {}


def set_language(code):
    global _CURRENT, _STRINGS
    if code not in ("en", "ro"):
        code = "en"
    _CURRENT = code
    _STRINGS = _load_json(code)
    if not _STRINGS:
        load_fallback()
        _STRINGS = _FALLBACK


def get_language():
    return _CURRENT


def t(key, **fmt):
    """Translate a key, with fallback to English, then to the key itself."""
    text = _STRINGS.get(key)
    if text is None:
        # try fallback
        if _FALLBACK:
            text = _FALLBACK.get(key)
        if text is None:
            _MISSING.add(key)
            text = key
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def missing_keys():
    """Return set of keys that were requested but not found."""
    return set(_MISSING)


def clear_missing():
    _MISSING.clear()


# Initialize
load_fallback()
set_language("en")
