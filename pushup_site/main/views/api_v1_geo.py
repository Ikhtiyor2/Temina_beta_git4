"""Geo autocomplete for Uzbekistan regions and cities."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from main.geo_uz import list_cities, list_regions
from main.locale_content import normalize_lang
from main.views.api_v1_helpers import request_lang, require_authenticated_json


def _lang(request) -> str:
    """Prefer ?lang=, then Accept-Language (same as other v1 APIs)."""
    raw = (request.GET.get("lang") or "").strip()
    if raw:
        return normalize_lang(raw)
    return request_lang(request)


@require_GET
def api_v1_geo_regions(request):
    err = require_authenticated_json(request)
    if err:
        return err
    q = (request.GET.get("q") or "").strip()
    lang = _lang(request)
    results = list_regions(q=q, lang=lang)
    return JsonResponse({"country": "UZ", "results": results})


@require_GET
def api_v1_geo_cities(request):
    err = require_authenticated_json(request)
    if err:
        return err
    q = (request.GET.get("q") or "").strip()
    region = (request.GET.get("region") or "").strip()
    region_id = (request.GET.get("regionId") or "").strip()
    lang = _lang(request)
    results = list_cities(region=region, region_id=region_id, q=q, lang=lang)[:40]
    return JsonResponse({"country": "UZ", "results": results})
