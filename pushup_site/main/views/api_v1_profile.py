"""GET/PATCH /api/v1/users/me/ and skill upgrades."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from main.models import Institution, Player
from main.profile_helpers import serialize_player_me
from main.views.api_v1_helpers import json_error, parse_json_body, request_lang, require_authenticated_json


def _get_player(request) -> Player:
    player, _ = Player.objects.get_or_create(user=request.user)
    return player


@require_http_methods(["GET", "PATCH"])
def api_v1_users_me(request):
    err = require_authenticated_json(request)
    if err:
        return err
    player = _get_player(request)
    lang = request_lang(request)
    if request.method == "GET":
        return JsonResponse(serialize_player_me(player, lang=lang))

    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None

    if not player.telegram_id:
        if "displayName" in body:
            player.display_name = str(body.get("displayName") or "")[:120]
        if "avatarUrl" in body:
            player.avatar_url = str(body.get("avatarUrl") or "")[:512]
    if "city" in body:
        player.city = str(body.get("city") or "")[:120]
    if "region" in body:
        player.region = str(body.get("region") or "")[:120]
    if "faculty" in body:
        player.faculty = str(body.get("faculty") or "")[:200]
    if "course" in body:
        course = body.get("course")
        player.course = int(course) if course is not None and str(course).isdigit() else None
    if "institutionCustom" in body:
        player.institution_custom = str(body.get("institutionCustom") or "")[:200]
    if "institutionId" in body:
        inst_id = body.get("institutionId")
        if inst_id:
            try:
                player.institution = Institution.objects.get(pk=int(inst_id))
                player.institution_custom = ""
            except (Institution.DoesNotExist, TypeError, ValueError):
                return json_error("Institution not found", status=400, code="invalid_institution")
        else:
            player.institution = None
    if "schoolInstitutionId" in body:
        sid = body.get("schoolInstitutionId")
        if sid:
            try:
                player.school_institution = Institution.objects.get(
                    pk=int(sid), type=Institution.TYPE_SCHOOL
                )
            except (Institution.DoesNotExist, TypeError, ValueError):
                return json_error("School not found", status=400, code="invalid_school")
        else:
            player.school_institution = None
    if "schoolCustom" in body:
        school_name = str(body.get("schoolCustom") or "").strip()
        if not school_name:
            player.school_institution = None
        else:
            school, _ = Institution.objects.get_or_create(
                type=Institution.TYPE_SCHOOL,
                name=school_name[:200],
                city=player.city or "",
                defaults={
                    "region": player.region or "",
                    "country": "UZ",
                    "is_verified": False,
                    "submitted_by": request.user,
                },
            )
            player.school_institution = school

    player.save()
    return JsonResponse(serialize_player_me(player, lang=lang))


@require_http_methods(["POST"])
def api_v1_users_me_upgrade_skill(request):
    err = require_authenticated_json(request)
    if err:
        return err
    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None
    skill = str(body.get("skill") or "").lower()
    player = _get_player(request)
    if not player.upgrade_skill(skill):
        return json_error("Cannot upgrade skill", status=400, code="upgrade_failed")
    player.save()
    return JsonResponse({"success": True, "profile": serialize_player_me(player, lang=request_lang(request))})
