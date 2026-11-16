"""Institution search and custom submit."""

from django.db.models import Case, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from main.locale_content import localize_place, localized_institution_name, normalize_lang
from main.models import Institution, Player
from main.views.api_v1_helpers import json_error, parse_json_body, request_lang, require_authenticated_json


def _serialize_institution(inst: Institution, lang: str = "ru") -> dict:
    return {
        "id": inst.id,
        "type": inst.type,
        "name": localized_institution_name(inst, lang),
        "nameRu": inst.name,
        "nameEn": inst.name_en,
        "nameUz": inst.name_uz,
        "city": localize_place(inst.city, lang, kind="city"),
        "cityRu": inst.city,
        "region": localize_place(inst.region, lang, kind="region"),
        "regionRu": inst.region,
        "country": inst.country,
        "isVerified": inst.is_verified,
    }


def _order_by_geo_preference(qs, *, city: str, region: str):
    """Rank local matches first without excluding other regions."""
    if not city and not region:
        return qs.order_by("-is_verified", "name")
    whens: list[When] = []
    rank = 0
    if city and region:
        whens.append(
            When(
                Q(city__icontains=city) & Q(region__icontains=region),
                then=Value(rank),
            )
        )
        rank += 1
    if city:
        whens.append(When(city__icontains=city, then=Value(rank)))
        rank += 1
    if region:
        whens.append(When(region__icontains=region, then=Value(rank)))
        rank += 1
    return qs.annotate(
        geo_rank=Case(*whens, default=Value(rank), output_field=IntegerField())
    ).order_by("geo_rank", "-is_verified", "name")


@require_GET
def api_v1_institutions_search(request):
    err = require_authenticated_json(request)
    if err:
        return err
    q = (request.GET.get("q") or "").strip()
    inst_type = (request.GET.get("type") or Institution.TYPE_UNIVERSITY).strip()
    city = (request.GET.get("city") or "").strip()
    region = (request.GET.get("region") or "").strip()
    country = (request.GET.get("country") or "UZ").strip().upper() or "UZ"
    lang = normalize_lang(request.GET.get("lang")) if request.GET.get("lang") else request_lang(request)
    qs = Institution.objects.filter(country=country)
    if inst_type in {Institution.TYPE_UNIVERSITY, Institution.TYPE_SCHOOL}:
        qs = qs.filter(type=inst_type)
    if q:
        # Search across all language fields so users can type in any language.
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(name_en__icontains=q)
            | Q(name_uz__icontains=q)
            | Q(city__icontains=q)
            | Q(region__icontains=q)
        )
    else:
        qs = qs.filter(is_verified=True)
    qs = _order_by_geo_preference(qs, city=city, region=region)
    limit = min(int(request.GET.get("limit") or 50), 80)
    results = [_serialize_institution(i, lang=lang) for i in qs[:limit]]
    return JsonResponse({"results": results, "country": country})


@require_POST
def api_v1_institutions_create(request):
    err = require_authenticated_json(request)
    if err:
        return err
    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None
    name = (body.get("name") or "").strip()
    if not name:
        return json_error("name is required", status=400, code="invalid_name")
    inst_type = body.get("type") or Institution.TYPE_UNIVERSITY
    if inst_type not in {Institution.TYPE_UNIVERSITY, Institution.TYPE_SCHOOL}:
        inst_type = Institution.TYPE_UNIVERSITY
    inst = Institution.objects.create(
        type=inst_type,
        name=name[:200],
        name_en=str(body.get("nameEn") or "")[:200],
        name_uz=str(body.get("nameUz") or "")[:200],
        city=str(body.get("city") or "")[:120],
        region=str(body.get("region") or "")[:120],
        country=str(body.get("country") or "UZ")[:80],
        is_verified=False,
        submitted_by=request.user,
    )
    return JsonResponse(_serialize_institution(inst, lang=request_lang(request)), status=201)
