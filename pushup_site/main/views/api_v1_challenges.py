"""PvP challenges with XP wager."""

from datetime import timedelta

from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from main.models import Challenge, Friendship, Player, WorkoutSession
from main.profile_helpers import total_xp
from main.views.api_v1_helpers import json_error, parse_json_body, require_authenticated_json

MIN_WAGER = 10
MAX_WAGER = 500
CANONICAL = {"PUSHUP", "SQUAT", "PULLUP", "CRUNCH", "TABATA", "RUN"}


def _me(request) -> Player:
    player, _ = Player.objects.get_or_create(user=request.user)
    return player


def _are_friends(a: Player, b: Player) -> bool:
    return Friendship.objects.filter(
        Q(from_player=a, to_player=b, status=Friendship.STATUS_ACCEPTED)
        | Q(from_player=b, to_player=a, status=Friendship.STATUS_ACCEPTED)
    ).exists()


def _available_xp(player: Player) -> int:
    return max(0, total_xp(player) - int(player.xp_escrow or 0))


def _release_escrow(ch: Challenge) -> None:
    wager = ch.wager_xp
    ch.challenger.xp_escrow = max(0, int(ch.challenger.xp_escrow or 0) - wager)
    ch.opponent.xp_escrow = max(0, int(ch.opponent.xp_escrow or 0) - wager)
    ch.challenger.save(update_fields=["xp_escrow"])
    ch.opponent.save(update_fields=["xp_escrow"])


def _serialize_challenge(ch: Challenge) -> dict:
    return {
        "id": ch.id,
        "challengerId": ch.challenger_id,
        "opponentId": ch.opponent_id,
        "exerciseType": ch.exercise_type,
        "goalMetric": ch.goal_metric,
        "goalValue": ch.goal_value,
        "wagerXp": ch.wager_xp,
        "deadline": ch.deadline.isoformat(),
        "status": ch.status,
        "challengerResult": ch.challenger_result,
        "opponentResult": ch.opponent_result,
        "winnerId": ch.winner_id,
    }


def _validate_session(player: Player, session_id, exercise_type: str, result: int) -> str | None:
    if not session_id:
        return None
    try:
        sid = int(session_id)
    except (TypeError, ValueError):
        return "Invalid sessionId"
    try:
        session = WorkoutSession.objects.get(pk=sid, player=player)
    except WorkoutSession.DoesNotExist:
        return "Workout session not found"
    if (session.exercise_type or "").upper() != exercise_type.upper():
        return "Session exercise type mismatch"
    if int(session.reps_count or 0) < int(result):
        return "Result exceeds session reps"
    return None


@require_GET
def api_v1_challenges_list(request):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    qs = Challenge.objects.filter(Q(challenger=me) | Q(opponent=me)).order_by("-created_at")[:50]
    return JsonResponse({"challenges": [_serialize_challenge(c) for c in qs]})


@require_http_methods(["POST"])
def api_v1_challenges_create(request):
    err = require_authenticated_json(request)
    if err:
        return err
    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None
    me = _me(request)
    opponent_id = int(body.get("opponentId") or 0)
    try:
        opponent = Player.objects.get(pk=opponent_id)
    except Player.DoesNotExist:
        return json_error("Opponent not found", status=404, code="opponent_not_found")
    if opponent.id == me.id:
        return json_error("Cannot challenge yourself", status=400, code="invalid_opponent")
    if not _are_friends(me, opponent):
        return json_error("Must be friends", status=400, code="not_friends")
    exercise_type = str(body.get("exerciseType") or "PUSHUP").upper()
    if exercise_type not in CANONICAL:
        return json_error("Invalid exercise", status=400, code="invalid_exercise")
    wager = int(body.get("wagerXp") or MIN_WAGER)
    wager = max(MIN_WAGER, min(MAX_WAGER, wager))
    if _available_xp(me) < wager:
        return json_error("Insufficient XP for wager", status=400, code="insufficient_xp")
    hours = int(body.get("deadlineHours") or 48)
    hours = max(24, min(72, hours))
    ch = Challenge.objects.create(
        challenger=me,
        opponent=opponent,
        exercise_type=exercise_type,
        goal_metric=str(body.get("goalMetric") or Challenge.METRIC_REPS),
        goal_value=int(body.get("goalValue") or 0),
        wager_xp=wager,
        deadline=timezone.now() + timedelta(hours=hours),
    )
    return JsonResponse(_serialize_challenge(ch), status=201)


@require_http_methods(["POST"])
def api_v1_challenges_accept(request, challenge_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    try:
        ch = Challenge.objects.select_related("challenger", "opponent").get(
            pk=challenge_id, opponent=me, status=Challenge.STATUS_PENDING
        )
    except Challenge.DoesNotExist:
        return json_error("Challenge not found", status=404, code="not_found")
    if ch.deadline <= timezone.now():
        ch.status = Challenge.STATUS_EXPIRED
        ch.save(update_fields=["status"])
        return json_error("Challenge expired", status=400, code="expired")
    wager = ch.wager_xp
    if _available_xp(me) < wager or _available_xp(ch.challenger) < wager:
        return json_error("Insufficient XP for wager", status=400, code="insufficient_xp")
    ch.challenger.xp_escrow += wager
    me.xp_escrow += wager
    ch.challenger.save(update_fields=["xp_escrow"])
    me.save(update_fields=["xp_escrow"])
    ch.status = Challenge.STATUS_ACTIVE
    ch.save(update_fields=["status"])
    return JsonResponse(_serialize_challenge(ch))


@require_http_methods(["POST"])
def api_v1_challenges_decline(request, challenge_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    try:
        ch = Challenge.objects.get(pk=challenge_id, opponent=me, status=Challenge.STATUS_PENDING)
    except Challenge.DoesNotExist:
        return json_error("Challenge not found", status=404, code="not_found")
    ch.status = Challenge.STATUS_CANCELLED
    ch.save(update_fields=["status"])
    return JsonResponse(_serialize_challenge(ch))


@require_http_methods(["POST"])
def api_v1_challenges_cancel(request, challenge_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    try:
        ch = Challenge.objects.get(pk=challenge_id, challenger=me, status=Challenge.STATUS_PENDING)
    except Challenge.DoesNotExist:
        return json_error("Challenge not found", status=404, code="not_found")
    ch.status = Challenge.STATUS_CANCELLED
    ch.save(update_fields=["status"])
    return JsonResponse(_serialize_challenge(ch))


@require_http_methods(["POST"])
def api_v1_challenges_submit(request, challenge_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None
    me = _me(request)
    try:
        ch = Challenge.objects.select_related("challenger", "opponent").get(
            pk=challenge_id, status=Challenge.STATUS_ACTIVE
        )
    except Challenge.DoesNotExist:
        return json_error("Challenge not found", status=404, code="not_found")
    if me.id not in {ch.challenger_id, ch.opponent_id}:
        return json_error("Forbidden", status=403, code="forbidden")
    result = int(body.get("result") or 0)
    flags = body.get("integrity", {}).get("flags", []) if isinstance(body.get("integrity"), dict) else []
    if flags:
        ch.status = Challenge.STATUS_CANCELLED
        _release_escrow(ch)
        ch.save(update_fields=["status"])
        return json_error("Challenge voided due to integrity flags", status=400, code="integrity_void")

    session_id = body.get("sessionId")
    session_err = _validate_session(me, session_id, ch.exercise_type, result)
    if session_err:
        return json_error(session_err, status=400, code="invalid_session")

    if me.id == ch.challenger_id:
        ch.challenger_result = result
        if session_id:
            ch.session_challenger_id = int(session_id)
    else:
        ch.opponent_result = result
        if session_id:
            ch.session_opponent_id = int(session_id)
    ch.save()

    if ch.challenger_result > 0 and ch.opponent_result > 0:
        _resolve_challenge(ch)
    return JsonResponse(_serialize_challenge(ch))


def _resolve_challenge(ch: Challenge) -> None:
    wager = ch.wager_xp
    _release_escrow(ch)
    if ch.challenger_result > ch.opponent_result:
        ch.winner = ch.challenger
        ch.challenger.add_exp(wager)
        ch.opponent.deduct_exp(wager)
    elif ch.opponent_result > ch.challenger_result:
        ch.winner = ch.opponent
        ch.opponent.add_exp(wager)
        ch.challenger.deduct_exp(wager)
    else:
        ch.winner = None
    ch.challenger.save()
    ch.opponent.save()
    ch.status = Challenge.STATUS_COMPLETED
    ch.save(update_fields=["status", "winner_id", "challenger_result", "opponent_result"])
