"""Shared localization helpers for geo places and institutions."""

from __future__ import annotations

from main.geo_uz import UZ_CITIES, UZ_REGIONS, _pick


def normalize_lang(raw: str | None) -> str:
    key = (raw or "ru").strip().lower()[:5]
    if key.startswith("en"):
        return "en"
    if key.startswith("uz"):
        return "uz"
    return "ru"


def localized_institution_name(inst, lang: str) -> str:
    """Return best institution name for lang; fall back to Russian."""
    key = normalize_lang(lang)
    if key == "en" and getattr(inst, "name_en", None):
        return inst.name_en
    if key == "uz" and getattr(inst, "name_uz", None):
        return inst.name_uz
    return inst.name


def localize_place(ru_name: str, lang: str, *, kind: str) -> str:
    needle = (ru_name or "").strip().lower()
    if not needle:
        return ""
    source = UZ_CITIES if kind == "city" else UZ_REGIONS
    for item in source:
        if item["name"].lower() == needle:
            return _pick(lang, item["name"], item.get("nameEn", ""), item.get("nameUz", ""))
    return ru_name
