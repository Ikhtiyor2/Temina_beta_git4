from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from django.db.models import Avg, Sum
from django.utils import timezone

from .models import FitnessProfile, WorkoutSession

EXERCISES: List[str] = ["PUSHUP", "SQUAT", "PULLUP", "CRUNCH", "TABATA", "RUN"]


@dataclass(frozen=True)
class QuestPersonalizationProfile:
    preparedness_score: float
    difficulty_tier: int
    daily_slots: int
    exercise_goals: Dict[str, int]
    include_combo: bool
    include_perfect_form: bool
    include_streak: bool
    include_rest: bool
    source_profile: str


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _fitness_level_score(profile: FitnessProfile | None) -> float:
    if not profile:
        return 0.25
    level_map = {"beginner": 0.2, "intermediate": 0.5, "advanced": 0.85}
    return level_map.get((profile.fitness_level or "beginner").lower(), 0.2)


def _activity_level_score(profile: FitnessProfile | None) -> float:
    if not profile:
        return 0.25
    level_map = {
        "sedentary": 0.15,
        "light": 0.3,
        "moderate": 0.5,
        "active": 0.72,
        "very_active": 0.9,
    }
    return level_map.get((profile.activity_level or "moderate").lower(), 0.5)


def _weekly_target_score(profile: FitnessProfile | None) -> float:
    if not profile:
        return 0.25
    per_week = profile.workouts_per_week or 3
    return _clamp((per_week - 1) / 6.0, 0.1, 1.0)


def _history_score(player) -> float:
    month_ago = timezone.now() - timezone.timedelta(days=30)
    qs = WorkoutSession.objects.filter(player=player, date__gte=month_ago)
    if not qs.exists():
        return 0.2

    agg = qs.aggregate(
        total_reps=Sum("reps_count"),
        avg_reps=Avg("reps_count"),
    )
    total_reps = float(agg.get("total_reps") or 0)
    avg_reps = float(agg.get("avg_reps") or 0)
    session_count = float(qs.count())

    reps_component = _clamp(total_reps / 2000.0, 0.0, 1.0)
    avg_component = _clamp(avg_reps / 80.0, 0.0, 1.0)
    frequency_component = _clamp(session_count / 20.0, 0.0, 1.0)
    return _clamp(
        reps_component * 0.45 + avg_component * 0.25 + frequency_component * 0.30,
        0.0,
        1.0,
    )


def build_quest_personalization(player) -> QuestPersonalizationProfile:
    profile = FitnessProfile.objects.filter(user=player.user).first()

    profile_signal = (
        _fitness_level_score(profile) * 0.45
        + _activity_level_score(profile) * 0.35
        + _weekly_target_score(profile) * 0.20
    )
    history_signal = _history_score(player)
    level_signal = _clamp((max(1, player.level) - 1) / 20.0, 0.0, 1.0)
    fatigue_penalty = _clamp((player.fatigue or 0) / 100.0, 0.0, 1.0) * 0.2

    preparedness = _clamp(
        profile_signal * 0.45 + history_signal * 0.35 + level_signal * 0.20 - fatigue_penalty,
        0.05,
        1.0,
    )

    if preparedness < 0.33:
        tier = 1
    elif preparedness < 0.66:
        tier = 2
    else:
        tier = 3

    # goals for one quest event of each exercise
    multipliers = {
        1: {"PUSHUP": 10, "SQUAT": 16, "PULLUP": 4, "CRUNCH": 18, "TABATA": 1, "RUN": 1},
        2: {"PUSHUP": 16, "SQUAT": 24, "PULLUP": 7, "CRUNCH": 26, "TABATA": 1, "RUN": 2},
        3: {"PUSHUP": 24, "SQUAT": 34, "PULLUP": 11, "CRUNCH": 36, "TABATA": 2, "RUN": 3},
    }
    base = multipliers[tier]

    level_bonus = max(0, player.level - 1)
    goals = {
        "PUSHUP": int(base["PUSHUP"] + level_bonus * 1.2),
        "SQUAT": int(base["SQUAT"] + level_bonus * 1.6),
        "PULLUP": int(base["PULLUP"] + level_bonus * 0.8),
        "CRUNCH": int(base["CRUNCH"] + level_bonus * 1.8),
        "TABATA": int(base["TABATA"] + level_bonus * 0.2),
        "RUN": int(base["RUN"] + level_bonus * 0.3),
    }

    include_rest = (player.fatigue or 0) >= 65
    return QuestPersonalizationProfile(
        preparedness_score=preparedness,
        difficulty_tier=tier,
        daily_slots=5 if tier >= 2 else 4,
        exercise_goals=goals,
        include_combo=tier >= 2,
        include_perfect_form=tier >= 2,
        include_streak=True,
        include_rest=include_rest,
        source_profile="hybrid",
    )
