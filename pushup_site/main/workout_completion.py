"""Shared workout finish pipeline: XP, stats, quests, integrity audit."""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from main.integrity import sanitize_client_reps
from main.models import IntegrityFlag, Player, PlayerStats, WorkoutSession, WorkoutSet
from main.quest_manager import QuestManager

logger = logging.getLogger(__name__)

CANONICAL_EXERCISE_TYPES = frozenset({"PUSHUP", "SQUAT", "PULLUP", "CRUNCH", "TABATA", "RUN"})
STRENGTH_EXERCISES = {"PUSHUP", "PULLUP"}


def apply_skill_bonuses(player, exercise_type, reps, base_calories):
    """Returns (calories with bonus, total xp, base xp, skill bonus xp)."""
    strength = max(0, getattr(player, "strength", 1) - 1)
    stamina = max(0, getattr(player, "stamina", 1) - 1)
    agility = max(0, getattr(player, "agility", 1) - 1)
    technique = max(0, getattr(player, "technique", 1) - 1)

    cal_mult = 1.0 + stamina * 0.03
    calories = base_calories * cal_mult

    # No participation XP for empty sessions — only counted reps/activity earn XP.
    base_xp = max(0, int(reps))
    if base_xp <= 0:
        return round(calories, 1), 0, 0, 0

    xp_mult = 1.0
    if exercise_type in STRENGTH_EXERCISES:
        xp_mult += strength * 0.05
    xp_mult += agility * 0.03
    xp_mult += technique * 0.05

    total_xp_val = max(1, int(base_xp * xp_mult))
    skill_bonus = max(0, total_xp_val - base_xp)
    return round(calories, 1), total_xp_val, base_xp, skill_bonus

_EXERCISE_ALIASES = {
    "PUSHUPS": "PUSHUP",
    "PUSHUP": "PUSHUP",
    "SQUATS": "SQUAT",
    "SQUAT": "SQUAT",
    "CRUNCHES": "CRUNCH",
    "CRUNCH": "CRUNCH",
    "PULLUPS": "PULLUP",
    "PULLUP": "PULLUP",
    "TABATA": "TABATA",
    "RUN": "RUN",
}


def normalize_exercise_type(raw: str | None) -> str:
    key = (raw or "PUSHUP").strip().upper()
    return _EXERCISE_ALIASES.get(key, key if key in CANONICAL_EXERCISE_TYPES else "PUSHUP")


def _get_or_create_stats(player: Player) -> PlayerStats:
    stats, _ = PlayerStats.objects.get_or_create(player=player)
    return stats


def record_integrity_flag(
    player: Player,
    session_id: int | None,
    *,
    integrity: dict[str, Any] | None,
    sanitized_reps: int,
    raw_reps: int,
) -> None:
    if not isinstance(integrity, dict) or not integrity:
        return
    flags = integrity.get("flags") or []
    if not flags and sanitized_reps >= raw_reps:
        return
    IntegrityFlag.objects.create(
        player=player,
        session_id=session_id,
        flags=list(flags) if isinstance(flags, list) else [],
        sanitized_reps=sanitized_reps,
        raw_reps=raw_reps,
        payload=integrity,
    )


def compute_tabata_calories(player: Player, duration: int, reps: int, intensity_score: float, client_cal: float | None) -> float:
    if client_cal is not None:
        return float(client_cal)
    met = 10.0 + min(max(intensity_score, 0.35), 1.0) * 4.0
    weight_kg = 70.0
    try:
        assessment = getattr(player.user, "fitness_assessments", None)
        if assessment is not None:
            latest = assessment.order_by("-assessment_completed_at").first()
            if latest and getattr(latest, "weight_kg", None):
                weight_kg = float(latest.weight_kg)
    except Exception:
        pass
    active = max(duration * 0.55, float(reps) * 0.8)
    return met * weight_kg * (active / 3600.0) + float(reps) * 0.12


def compute_run_xp(distance_km: float, duration_sec: int) -> int:
    base = int(distance_km * 50) + max(1, duration_sec // 60)
    return max(1, base)


def finalize_workout(
    player: Player,
    *,
    exercise_type: str,
    reps: int,
    duration_sec: int = 0,
    calories: float | None = None,
    errors_count: int = 0,
    integrity: dict[str, Any] | None = None,
    server_count: int | None = None,
    intensity_score: float = 0.0,
    user=None,
    update_quests: bool = True,
    existing_session: WorkoutSession | None = None,
) -> dict[str, Any]:
    """Persist session, award XP, update stats and quests."""
    exercise_type = normalize_exercise_type(exercise_type)
    raw_reps = max(0, int(reps or 0))
    reps = sanitize_client_reps(
        raw_reps,
        server_count=server_count,
        integrity=integrity if isinstance(integrity, dict) else None,
    )
    duration_sec = max(0, int(duration_sec or 0))

    if exercise_type == "TABATA":
        base_calories = compute_tabata_calories(player, duration_sec, reps, intensity_score, calories)
    elif exercise_type == "RUN":
        base_calories = float(calories or 0) or max(1.0, duration_sec * 0.08)
    else:
        base_calories = float(calories or 0) or float(reps) * 0.5

    calories_final, xp_earned, base_xp, skill_bonus = apply_skill_bonuses(
        player, exercise_type, reps, base_calories
    )
    if exercise_type == "RUN":
        distance_km = float((integrity or {}).get("distance_km") or 0)
        run_xp = compute_run_xp(distance_km, duration_sec)
        _, xp_earned, base_xp, skill_bonus = apply_skill_bonuses(player, "SQUAT", run_xp, 0)

    leveled_up = False
    if xp_earned > 0:
        leveled_up = player.add_exp(xp_earned)
    player.save()

    session = existing_session
    if session is None:
        session = WorkoutSession.objects.create(
            player=player,
            exercise_type=exercise_type,
            reps_count=reps,
            duration_seconds=duration_sec,
            calories_burned=calories_final,
            errors_count=max(0, errors_count),
        )
    else:
        session.exercise_type = exercise_type
        session.reps_count = reps
        session.duration_seconds = duration_sec
        session.calories_burned = calories_final
        session.errors_count = max(0, errors_count)
        session.save(
            update_fields=[
                "exercise_type",
                "reps_count",
                "duration_seconds",
                "calories_burned",
                "errors_count",
            ]
        )

    record_integrity_flag(
        player,
        session.id,
        integrity=integrity,
        sanitized_reps=reps,
        raw_reps=raw_reps,
    )

    if user is not None and reps > 0 and exercise_type in {"PUSHUP", "SQUAT", "PULLUP", "CRUNCH"}:
        try:
            WorkoutSet.objects.create(
                user=user,
                exercise_type=exercise_type,
                repetitions=reps,
                quality_score=1.0,
            )
        except Exception:
            logger.exception("WorkoutSet create failed")

    stats = _get_or_create_stats(player)
    is_record = False
    if exercise_type in {"PUSHUP", "SQUAT", "PULLUP", "CRUNCH"}:
        stats.update_daily_stats(reps, calories_final)
        is_record = stats.update_exercise_stats(exercise_type, reps, is_record=True)
        stats.total_workout_time += duration_sec
        stats.save(update_fields=["total_workout_time"])
    elif exercise_type == "TABATA":
        stats.update_daily_stats(reps, calories_final)
        stats.total_workout_time += duration_sec
        stats.save(update_fields=["total_workout_time"])
    elif exercise_type == "RUN":
        stats.update_daily_stats(0, calories_final)
        stats.total_workout_time += duration_sec
        stats.save(update_fields=["total_workout_time"])

    quest_completed = []
    if update_quests:
        try:
            quest_completed = QuestManager(player).update_quest_progress(exercise_type, reps)
        except Exception:
            logger.exception("Quest progress update failed")

    return {
        "session_id": session.id,
        "exercise_type": exercise_type,
        "reps": reps,
        "duration_sec": duration_sec,
        "calories": round(calories_final, 1),
        "xp_earned": xp_earned,
        "xp_gained": xp_earned,
        "baseXp": base_xp,
        "skillBonus": skill_bonus,
        "totalXp": xp_earned,
        "leveled_up": leveled_up,
        "quests_completed": len(quest_completed),
    }
