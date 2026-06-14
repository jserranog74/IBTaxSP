from __future__ import annotations


SUPPORTED_LANGUAGES = {"es", "en"}


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return "es"
    normalized = lang.lower()
    if normalized not in SUPPORTED_LANGUAGES:
        return "es"
    return normalized
