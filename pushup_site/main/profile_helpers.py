"""Shared profile and leaderboard serialization."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from main.locale_content import localize_place, localized_institution_name
from main.models import Challenge, Friendship, Player, PlayerStats, RunSession, WorkoutSession


def total_xp(player: Player) -> int:
    level = getattr(player, "level", 1) or 1
    exp = float(getattr(player, "exp", 0) or 0)
    return int(100 * level * (level - 1) / 2 + exp)


def level_class(level: int) -> str:
    if level >= 20:
        return "MASTER"
    if level >= 15:
        return "EXPERT"
    if level >= 10:
        return "FIGHTER"
    if level >= 5:
        return "ATHLETE"
    return "BEGINNER"


def friend_count(player: Player) -> int:
    return Friendship.objects.filter(
        Q(from_player=player, status=Friendship.STATUS_ACCEPTED)
        | Q(to_player=player, status=Friendship.STATUS_ACCEPTED)
    ).count()


def _friend_ids(player: Player) -> set[int]:
    ids: set[int] = set()
    for fr in Friendship.objects.filter(
        Q(from_player=player, status=Friendship.STATUS_ACCEPTED)
        | Q(to_player=player, status=Friendship.STATUS_ACCEPTED)
    ):
        if fr.from_player_id == player.id:
            ids.add(fr.to_player_id)
        else:
            ids.add(fr.from_player_id)
    return ids


def mutual_friend_count(viewer: Player | None, target: Player) -> int:
    if viewer is None or viewer.id == target.id:
        return 0
    return len(_friend_ids(viewer) & _friend_ids(target))


def friendship_status(viewer: Player | None, target: Player) -> str:
    if viewer is None or viewer.id == target.id:
        return "none"
    fr = Friendship.objects.filter(
        Q(from_player=viewer, to_player=target) | Q(from_player=target, to_player=viewer)
    ).first()
    if not fr:
        return "none"
    if fr.status == Friendship.STATUS_ACCEPTED:
        return "accepted"
    if fr.status == Friendship.STATUS_PENDING:
        if fr.from_player_id == viewer.id:
            return "pending_out"
        return "pending_in"
    return "none"


def institution_label(player: Player, lang: str = "ru") -> dict | None:
    if player.institution_id:
        inst = player.institution
        name = localized_institution_name(inst, lang) if inst else player.institution_custom
    elif player.institution_custom:
        name = player.institution_custom
    else:
        return None
    return {
        "id": player.institution_id,
        "name": name,
        "faculty": player.faculty or "",
        "course": player.course,
        "custom": bool(player.institution_custom and not player.institution_id),
    }


def school_institution_label(player: Player, lang: str = "ru") -> dict | None:
    if not player.school_institution_id:
        return None
    inst = player.school_institution
    if not inst:
        return None
    return {
        "id": inst.id,
        "name": localized_institution_name(inst, lang),
        "city": localize_place(inst.city or "", lang, kind="city"),
    }


def player_badges(player: Player) -> list[dict]:
    return [
        {
            "id": b.id,
            "label": b.label,
            "icon": b.icon or "",
            "seasonId": b.season_id,
            "earnedAt": b.earned_at.isoformat(),
        }
        for b in player.badges.all()[:10]
    ]


def player_records(player: Player) -> dict:
    try:
        stats = player.stats
    except PlayerStats.DoesNotExist:
        return {}
    return {
        "maxPushups": stats.max_pushups_set,
        "maxSquats": stats.max_squats_set,
        "maxPullups": stats.max_pullups_set,
        "maxCrunches": stats.max_crunches_set,
    }


def workout_dates(player: Player) -> set:
    return set(WorkoutSession.objects.filter(player=player).dates("date", "day"))


def workout_streak(player: Player, today=None) -> int:
    """Подряд дни с хотя бы одной тренировкой. Сегодня можно ещё не тренироваться."""
    today = today or timezone.localdate()
    days = workout_dates(player)
    if not days:
        return 0
    cursor = today if today in days else today - timedelta(days=1)
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def training_snapshot(player: Player) -> dict:
    sessions = WorkoutSession.objects.filter(player=player)
    totals = sessions.aggregate(
        workouts=Count("id"),
        reps=Sum("reps_count"),
        calories=Sum("calories_burned"),
        duration=Sum("duration_seconds"),
    )
    user = player.user
    run_qs = RunSession.objects.none()
    if getattr(user, "id", None):
        run_qs = RunSession.objects.filter(user=user, status=RunSession.STATUS_FINISHED)
    run_totals = run_qs.aggregate(
        runs=Count("id"),
        distance=Sum("distance_km"),
        calories=Sum("calories_estimate"),
        duration=Sum("duration_sec"),
    )
    won = Challenge.objects.filter(winner=player).count()
    return {
        "workoutStreak": workout_streak(player),
        "totalWorkouts": int(totals["workouts"] or 0),
        "totalReps": int(totals["reps"] or 0),
        "totalCalories": round(float(totals["calories"] or 0) + float(run_totals.get("calories") or 0), 1),
        "totalMinutes": int(((totals["duration"] or 0) + (run_totals.get("duration") or 0)) / 60),
        "totalRuns": int(run_totals.get("runs") or 0),
        "totalDistanceKm": round(float(run_totals.get("distance") or 0), 2),
        "challengesWon": won,
        "fromTelegram": bool(player.telegram_id),
        "telegramUsername": player.telegram_username or "",
    }


def serialize_player_public(
    player: Player,
    *,
    rank: int | None = None,
    is_me: bool = False,
    viewer: Player | None = None,
    lang: str = "ru",
) -> dict:
    user = player.user
    inst = institution_label(player, lang=lang)
    status = friendship_status(viewer, player)
    return {
        "playerId": player.id,
        "username": user.username if user else "player",
        "displayName": player.display_name or (user.username if user else "player"),
        "avatarUrl": player.avatar_url or None,
        "level": int(player.level or 1),
        "totalXp": total_xp(player),
        "playerClass": level_class(int(player.level or 1)),
        "rank": rank,
        "city": localize_place(player.city or "", lang, kind="city"),
        "region": localize_place(player.region or "", lang, kind="region"),
        "institution": inst,
        "schoolInstitution": school_institution_label(player, lang=lang),
        "records": player_records(player),
        "friendCount": friend_count(player),
        "mutualFriendCount": mutual_friend_count(viewer, player),
        "isFriend": status == "accepted",
        "friendshipStatus": status,
        "badges": player_badges(player),
        "seasonTitle": player.season_title or "",
        "inviteCode": (player.invite_code or "") if is_me else "",
        "isMe": is_me,
    }


def serialize_player_me(player: Player, lang: str = "ru") -> dict:
    user = player.user
    payload = serialize_player_public(player, is_me=True, viewer=player, lang=lang)
    inst = institution_label(player, lang=lang)
    payload.update(
        {
            "email": user.email if user else "",
            "exp": float(player.exp or 0),
            "expToLevel": float(player.exp_to_level or 100),
            "skillPoints": int(player.skill_points or 0),
            "currency": int(player.currency or 0),
            "fatigue": float(player.fatigue or 0),
            "loginStreak": int(player.login_streak or 0),
            **training_snapshot(player),
            "friendCount": friend_count(player),
            "skills": {
                "strength": int(player.strength or 1),
                "stamina": int(player.stamina or 1),
                "agility": int(player.agility or 1),
                "technique": int(player.technique or 1),
            },
            "skillCap": player.skill_cap(),
            "schoolInstitutionId": player.school_institution_id,
            "schoolName": (school_institution_label(player, lang=lang) or {}).get("name", ""),
            "institutionCustom": player.institution_custom or "",
            "institutionId": inst["id"] if inst else None,
            "institutionName": inst["name"] if inst else "",
            "faculty": player.faculty or "",
            "course": player.course,
        }
    )
    return payload
