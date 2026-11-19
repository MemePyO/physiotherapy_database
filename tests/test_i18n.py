"""Consistency checks for the UI string table."""

import lang


def test_every_key_has_both_languages():
    for key, entry in lang.STRINGS.items():
        assert set(entry) >= set(lang.LANGS), key
        for code in lang.LANGS:
            assert entry[code].strip(), (key, code)


def test_translation_never_returns_the_key():
    original = lang.get_language()
    try:
        for code in lang.LANGS:
            lang.set_language(code)
            for key in lang.STRINGS:
                assert lang.t(key) != key, (code, key)
    finally:
        lang.set_language(original)


def test_format_placeholders_match_across_languages():
    import string

    formatter = string.Formatter()

    def fields(value: str) -> set[str]:
        try:
            return {
                name for _literal, name, _spec, _conv in formatter.parse(value) if name is not None
            }
        except ValueError:
            return set()

    for key, entry in lang.STRINGS.items():
        assert fields(entry["en"]) == fields(entry["ro"]), key
