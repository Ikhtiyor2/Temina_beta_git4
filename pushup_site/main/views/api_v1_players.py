"""Player search and public profiles."""

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from main.models import Friendship, Player
from main.profile_helpers import mutual_friend_count, serialize_player_public
from main.views.api_v1_helpers import json_error, request_lang, require_authenticated_json


def _me(request) -> Player:
    player, _ = Player.objects.get_or_create(user=request.user)
    return player


@require_GET
def api_v1_players_search(request):
    err = require_authenticated_json(request)
    if err:
        return err
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return json_error("Query too short", status=400, code="query_too_short")
    me = _me(request)
    lang = request_lang(request)
    qs = (
        Player.objects.select_related("user", "institution", "school_institution")
        .filter(
            user__is_active=True,
            user__is_staff=False,
            user__is_superuser=False,
        )
        .filter(Q(user__username__icontains=q) | Q(display_name__icontains=q))
        .exclude(pk=me.pk)[:20]
    )
    return JsonResponse(
        {
            "players": [
                serialize_player_public(p, viewer=me, lang=lang) for p in qs
            ]
        }
    )


@require_GET
def api_v1_friends_mutual(request, player_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    lang = request_lang(request)
    try:
        other = Player.objects.select_related("user", "institution").get(pk=player_id)
    except Player.DoesNotExist:
        return json_error("Player not found", status=404, code="player_not_found")
    my_friends = set()
    for fr in Friendship.objects.filter(
        Q(from_player=me, status=Friendship.STATUS_ACCEPTED)
        | Q(to_player=me, status=Friendship.STATUS_ACCEPTED)
    ).select_related("from_player__user", "to_player__user"):
        friend = fr.to_player if fr.from_player_id == me.id else fr.from_player
        my_friends.add(friend.id)
    other_friends = set()
    for fr in Friendship.objects.filter(
        Q(from_player=other, status=Friendship.STATUS_ACCEPTED)
        | Q(to_player=other, status=Friendship.STATUS_ACCEPTED)
    ).select_related("from_player__user", "to_player__user"):
        friend = fr.to_player if fr.from_player_id == other.id else fr.from_player
        other_friends.add(friend.id)
    mutual_ids = my_friends & other_friends
    mutual = (
        Player.objects.select_related("user", "institution")
        .filter(pk__in=mutual_ids)
        .order_by("id")[:50]
    )
    return JsonResponse(
        {
            "mutualFriendCount": len(mutual_ids),
            "mutualFriends": [serialize_player_public(p, viewer=me, lang=lang) for p in mutual],
        }
    )
