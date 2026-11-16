"""Friends and invite codes."""

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from main.models import Friendship, Player
from main.profile_helpers import serialize_player_public
from main.views.api_v1_helpers import json_error, parse_json_body, request_lang, require_authenticated_json

MAX_FRIENDS = 100


def _me(request) -> Player:
    player, _ = Player.objects.get_or_create(user=request.user)
    return player


def _friendship_between(a: Player, b: Player):
    return Friendship.objects.filter(
        Q(from_player=a, to_player=b) | Q(from_player=b, to_player=a)
    ).first()


@require_GET
def api_v1_friends_list(request):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    lang = request_lang(request)
    accepted = Friendship.objects.filter(
        Q(from_player=me, status=Friendship.STATUS_ACCEPTED)
        | Q(to_player=me, status=Friendship.STATUS_ACCEPTED)
    ).select_related("from_player__user", "to_player__user")
    friends = []
    for fr in accepted:
        other = fr.to_player if fr.from_player_id == me.id else fr.from_player
        entry = serialize_player_public(other, viewer=me, lang=lang)
        entry["friendshipId"] = fr.id
        friends.append(entry)
    incoming = Friendship.objects.filter(
        to_player=me, status=Friendship.STATUS_PENDING
    ).select_related("from_player__user")
    outgoing = Friendship.objects.filter(
        from_player=me, status=Friendship.STATUS_PENDING
    ).select_related("to_player__user")
    return JsonResponse(
        {
            "friends": friends,
            "friendCount": len(friends),
            "incoming": [
                {"friendshipId": fr.id, **serialize_player_public(fr.from_player, lang=lang)}
                for fr in incoming
            ],
            "outgoing": [
                {"friendshipId": fr.id, **serialize_player_public(fr.to_player, lang=lang)}
                for fr in outgoing
            ],
            "inviteCode": me.invite_code,
        }
    )


@require_http_methods(["POST"])
def api_v1_friends_request(request):
    err = require_authenticated_json(request)
    if err:
        return err
    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None
    me = _me(request)
    username = (body.get("username") or "").strip()
    player_id = body.get("playerId")
    target = None
    if player_id:
        target = Player.objects.filter(pk=int(player_id)).select_related("user").first()
    elif username:
        target = Player.objects.filter(user__username__iexact=username).select_related("user").first()
    if not target or target.id == me.id:
        return json_error("Player not found", status=404, code="player_not_found")
    if _friendship_between(me, target):
        return json_error("Friendship already exists", status=400, code="already_exists")
    from main.profile_helpers import friend_count

    if friend_count(me) >= MAX_FRIENDS:
        return json_error("Friend limit reached", status=400, code="friend_limit")
    fr = Friendship.objects.create(from_player=me, to_player=target, status=Friendship.STATUS_PENDING)
    return JsonResponse({"friendshipId": fr.id, "status": fr.status}, status=201)


@require_http_methods(["POST"])
def api_v1_friends_accept(request, friendship_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    try:
        fr = Friendship.objects.get(pk=friendship_id, to_player=me, status=Friendship.STATUS_PENDING)
    except Friendship.DoesNotExist:
        return json_error("Request not found", status=404, code="not_found")
    fr.status = Friendship.STATUS_ACCEPTED
    fr.save(update_fields=["status"])
    return JsonResponse({"success": True, "status": fr.status})


@require_http_methods(["DELETE"])
def api_v1_friends_delete(request, friendship_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    try:
        fr = Friendship.objects.get(
            pk=friendship_id,
        )
    except Friendship.DoesNotExist:
        return json_error("Not found", status=404, code="not_found")
    if fr.from_player_id != me.id and fr.to_player_id != me.id:
        return json_error("Forbidden", status=403, code="forbidden")
    fr.delete()
    return JsonResponse({"success": True})


@require_http_methods(["POST"])
def api_v1_friends_reject(request, friendship_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    try:
        fr = Friendship.objects.get(pk=friendship_id, to_player=me, status=Friendship.STATUS_PENDING)
    except Friendship.DoesNotExist:
        return json_error("Request not found", status=404, code="not_found")
    fr.delete()
    return JsonResponse({"success": True})


@require_http_methods(["POST"])
def api_v1_invites_redeem(request):
    err = require_authenticated_json(request)
    if err:
        return err
    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None
    code = (body.get("inviteCode") or body.get("code") or "").strip().upper()
    me = _me(request)
    inviter = Player.objects.filter(invite_code__iexact=code).select_related("user").first()
    if not inviter or inviter.id == me.id:
        return json_error("Invalid invite code", status=400, code="invalid_code")
    if _friendship_between(me, inviter):
        return JsonResponse({"success": True, "alreadyFriends": True})
    from main.profile_helpers import friend_count

    if friend_count(me) >= MAX_FRIENDS or friend_count(inviter) >= MAX_FRIENDS:
        return json_error("Friend limit reached", status=400, code="friend_limit")
    Friendship.objects.create(from_player=inviter, to_player=me, status=Friendship.STATUS_ACCEPTED)
    return JsonResponse({"success": True, "inviterUsername": inviter.user.username, "autoAccepted": True})
