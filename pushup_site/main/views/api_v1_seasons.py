"""GET /api/v1/seasons/current and rankings snapshots."""

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from main.leaderboard_service import leaderboard_queryset, season_leaderboard_queryset
from main.models import Player, Season, SeasonRanking
from main.profile_helpers import total_xp
from main.views.api_v1_helpers import json_error, require_authenticated_json


def _rank_for_player(me: Player, qs) -> int:
    from django.db.models import Q

    return (
        1
        + qs.filter(
            Q(level__gt=me.level)
            | (Q(level=me.level) & Q(exp__gt=me.exp))
            | (Q(level=me.level) & Q(exp=me.exp) & Q(pk__lt=me.pk))
        ).count()
    )


@require_GET
def api_v1_seasons_current(request):
    err = require_authenticated_json(request)
    if err:
        return err
    player, _ = Player.objects.get_or_create(user=request.user)
    now = timezone.now()
    seasons = Season.objects.filter(is_active=True, starts_at__lte=now, ends_at__gte=now).order_by("ends_at")
    payload = []
    for season in seasons:
        my_rank = None
        ranking = SeasonRanking.objects.filter(season=season, player=player).first()
        if ranking:
            my_rank = ranking.rank
        else:
            qs = season_leaderboard_queryset(season.scope, season.scope_key)
            if qs.filter(pk=player.pk).exists():
                my_rank = _rank_for_player(player, qs)
        days_left = max(0, (season.ends_at.date() - now.date()).days)
        payload.append(
            {
                "id": season.id,
                "name": season.name,
                "scope": season.scope,
                "scopeKey": season.scope_key,
                "startsAt": season.starts_at.isoformat(),
                "endsAt": season.ends_at.isoformat(),
                "prizeDescription": season.prize_description,
                "daysLeft": days_left,
                "myRank": my_rank,
            }
        )
    return JsonResponse({"seasons": payload})


@require_GET
def api_v1_season_rankings(request, season_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    try:
        season = Season.objects.get(pk=season_id)
    except Season.DoesNotExist:
        return json_error("Season not found", status=404, code="season_not_found")
    rankings = SeasonRanking.objects.filter(season=season).select_related("player__user").order_by("rank")[:100]
    return JsonResponse(
        {
            "seasonId": season.id,
            "seasonName": season.name,
            "scope": season.scope,
            "entries": [
                {
                    "rank": r.rank,
                    "totalXp": r.total_xp,
                    "snapshot": r.snapshot_json,
                }
                for r in rankings
            ],
        }
    )
