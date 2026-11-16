"""JSON leaderboard with scoped filters."""

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from main.leaderboard_service import leaderboard_queryset
from main.models import Player
from main.profile_helpers import level_class, serialize_player_public, total_xp
from main.views.api_v1_helpers import request_lang, require_authenticated_json


def _rank_for_player(me: Player, qs) -> int:
    return (
        1
        + qs.filter(
            Q(level__gt=me.level)
            | (Q(level=me.level) & Q(exp__gt=me.exp))
            | (Q(level=me.level) & Q(exp=me.exp) & Q(pk__lt=me.pk))
        ).count()
    )


@require_GET
def api_v1_leaderboard(request):
    err = require_authenticated_json(request)
    if err:
        return err
    try:
        limit = int(request.GET.get("limit", "30"))
    except (TypeError, ValueError):
        limit = 30
    limit = max(1, min(100, limit))
    scope = (request.GET.get("scope") or "global").lower()

    me, _ = Player.objects.get_or_create(user=request.user)
    lang = request_lang(request)
    qs = leaderboard_queryset(scope, me)
    total_players = qs.count()
    my_rank = _rank_for_player(me, qs) if total_players else 0

    top = qs.order_by("-level", "-exp", "id")[:limit]
    entries = []
    for i, p in enumerate(top, start=1):
        entry = serialize_player_public(p, rank=i, is_me=p.id == me.id, viewer=me, lang=lang)
        entries.append(entry)

    needs_profile = scope in {"city", "region", "university", "school"} and total_players == 0

    return JsonResponse(
        {
            "scope": scope,
            "myRank": my_rank,
            "totalPlayers": total_players,
            "myTotalXp": total_xp(me),
            "myLevel": int(me.level or 1),
            "myPlayerClass": level_class(int(me.level or 1)),
            "needsProfile": needs_profile,
            "entries": entries,
        }
    )


@require_GET
def api_v1_player_public(request, player_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    try:
        player = Player.objects.select_related("user", "institution").get(pk=player_id)
    except Player.DoesNotExist:
        from main.views.api_v1_helpers import json_error

        return json_error("Player not found", status=404, code="player_not_found")
    me, _ = Player.objects.get_or_create(user=request.user)
    lang = request_lang(request)
    qs = leaderboard_queryset("global", me)
    rank = _rank_for_player(player, qs)
    return JsonResponse(
        serialize_player_public(player, rank=rank, is_me=player.id == me.id, viewer=me, lang=lang)
    )
