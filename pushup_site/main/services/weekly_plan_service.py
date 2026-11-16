"""
Rule-based недельный план: комплекс упражнений на день из WORKOUT_CATALOG.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from main.models import FitnessAssessment, WeeklyPlan, WeeklyPlanDay, WeeklyPlanDayExercise
from main.views.api_v1_helpers import WORKOUT_CATALOG, get_workout

PARENT_ROTATION = ("PUSHUP", "SQUAT", "CRUNCH", "PULLUP")

DAY_COMPLEX_LABELS = (
    "Силовой комплекс",
    "Ноги и кор",
    "Верх и пресс",
    "Функциональный день",
    "Смешанная тренировка",
    "Силовой день",
    "Полный комплекс",
)


def catalog_ids() -> set[str]:
    return {w["id"] for w in WORKOUT_CATALOG}


def monday_of(d: date | None = None) -> date:
    d = d or timezone.now().date()
    return d - timedelta(days=d.weekday())


def _equipment_from_payload(payload: dict[str, Any]) -> set[str]:
    raw = payload.get("availableEquipment") or []
    if not isinstance(raw, list):
        return set()
    return {str(x) for x in raw}


def _health_slugs(payload: dict[str, Any]) -> set[str]:
    raw = payload.get("healthConditions") or payload.get("healthLimitations") or []
    if not isinstance(raw, list):
        return set()
    return {str(x) for x in raw}


def _workout_needs_equipment(w: dict[str, Any], need: str) -> bool:
    eq = w.get("equipment") or []
    return need in eq


def _filter_catalog_for_user(equipment: set[str], health: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for w in WORKOUT_CATALOG:
        wid = w["id"]
        if _workout_needs_equipment(w, "pullup_bar"):
            if "pullup_bar" not in equipment and "gym_access" not in equipment:
                continue
        if "knee" in health and wid in {"squat_jump", "squat_split"}:
            continue
        if "back" in health and wid in {"pushup_decline", "leg_raises"}:
            continue
        out.append(w)
    return out or list(WORKOUT_CATALOG)


def _workouts_by_parent(allowed: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for w in allowed:
        p = (w.get("parentType") or "").upper()
        by_parent.setdefault(p, []).append(w)
    return by_parent


def _pick_workout_for_parent(
    by_parent: dict[str, list[dict[str, Any]]],
    parent: str,
    fitness_level: int,
    tier: int,
    slot_offset: int = 0,
) -> dict[str, Any] | None:
    lst = by_parent.get(parent) or []
    if not lst:
        return None
    order = {"easy": 0, "medium": 1, "hard": 2}

    def diff_rank(wi: dict[str, Any]) -> int:
        return order.get(str(wi.get("difficulty") or "medium").lower(), 1)

    sorted_lst = sorted(lst, key=diff_rank)
    idx = min(max(fitness_level - 1, 0), len(sorted_lst) - 1)
    bump = min(tier - 1 + slot_offset, max(0, len(sorted_lst) - idx - 1))
    pick_idx = min(idx + bump, len(sorted_lst) - 1)
    return sorted_lst[pick_idx]


def _targets_for_workout(w: dict[str, Any], tier: int) -> dict[str, Any]:
    ex0 = (w.get("exercises") or [{}])[0]
    reps = int(ex0.get("reps") or 12)
    sets = int(ex0.get("sets") or 3)
    parent = (w.get("parentType") or "").upper()
    tier_bonus = max(0, tier - 1)
    return {
        "target_sets": sets + min(2, tier_bonus),
        "target_reps": reps + 2 * tier_bonus,
        "duration_sec": None,
    }


def _exercises_for_training_slot(
    slot: int,
    allowed: list[dict[str, Any]],
    fitness_level: int,
    tier: int,
) -> list[dict[str, Any]]:
    """3–4 упражнения разных типов; набор смещается по slot (день недели в ротации)."""
    by_parent = _workouts_by_parent(allowed)
    n = min(4, 3 + (tier - 1) // 4)
    exercises: list[dict[str, Any]] = []
    seen_parents: set[str] = set()

    for j in range(len(PARENT_ROTATION) + 2):
        if len(exercises) >= n:
            break
        parent = PARENT_ROTATION[(slot * 2 + j) % len(PARENT_ROTATION)]
        if parent in seen_parents:
            continue
        w = _pick_workout_for_parent(by_parent, parent, fitness_level, tier, slot_offset=slot + j)
        if not w:
            continue
        seen_parents.add(parent)
        targets = _targets_for_workout(w, tier)
        exercises.append(
            {
                "sort_order": len(exercises),
                "counter_profile_id": str(w["id"]),
                "display_title": str(w.get("title") or w["id"]),
                **targets,
            }
        )
    return exercises


def _schedule_indices(workouts_per_week: int) -> list[int]:
    n = max(1, min(7, int(workouts_per_week or 3)))
    if n == 1:
        return [2]
    if n == 2:
        return [1, 4]
    if n == 3:
        return [0, 2, 4]
    if n == 4:
        return [0, 2, 4, 6]
    if n == 5:
        return [0, 1, 3, 4, 6]
    if n == 6:
        return [0, 1, 2, 3, 4, 5]
    return [0, 1, 2, 3, 4, 5, 6]


def build_week_days(
    assessment: FitnessAssessment,
    tier: int,
) -> list[dict[str, Any]]:
    payload = assessment.payload if isinstance(assessment.payload, dict) else {}
    equipment = _equipment_from_payload(payload)
    health = _health_slugs(payload)
    fl = int(assessment.fitness_level or 3)
    wpw = int(assessment.workouts_per_week or 3)

    allowed = _filter_catalog_for_user(equipment, health)
    train_days = _schedule_indices(wpw)

    complexes_by_day: dict[int, dict[str, Any]] = {}
    for slot, day_ix in enumerate(train_days):
        ex_list = _exercises_for_training_slot(slot, allowed, fl, max(1, tier))
        if not ex_list:
            continue
        label = DAY_COMPLEX_LABELS[slot % len(DAY_COMPLEX_LABELS)]
        focus = " · ".join(e["display_title"] for e in ex_list[:3])
        if len(ex_list) > 3:
            focus += f" и ещё {len(ex_list) - 3}"
        complexes_by_day[day_ix] = {
            "display_title": label,
            "focus_note": focus[:250],
            "exercises": ex_list,
        }

    out: list[dict[str, Any]] = []
    for day_index in range(7):
        if day_index in complexes_by_day:
            c = complexes_by_day[day_index]
            out.append(
                {
                    "day_index": day_index,
                    "is_rest": False,
                    "display_title": c["display_title"],
                    "focus_note": c["focus_note"],
                    "exercises": c["exercises"],
                }
            )
        else:
            out.append(
                {
                    "day_index": day_index,
                    "is_rest": True,
                    "display_title": "Отдых",
                    "focus_note": "Восстановление и сон",
                    "exercises": [],
                }
            )
    return out


def session_met_target(
    *,
    parent_type: str,
    target_reps: int,
    target_sets: int,
    duration_target: int | None,
    reps: int,
    duration_sec: int,
) -> bool:
    if reps <= 0 and duration_sec <= 0:
        return False
    parent = (parent_type or "").upper()
    if duration_target and duration_target > 0:
        per_set = duration_target or 0
        total = per_set * max(1, target_sets)
        if total <= 0:
            return duration_sec >= 20
        return duration_sec >= int(total * 0.9)
    total_target = max(1, target_reps * max(1, target_sets))
    return reps >= int(total_target * 0.9)


@transaction.atomic
def replace_weekly_plan_for_user(
    user,
    assessment: FitnessAssessment,
    week_start: date | None = None,
    tier: int | None = None,
    source: str = "assessment",
) -> WeeklyPlan:
    week_start = week_start or monday_of()
    prev = (
        WeeklyPlan.objects.filter(user=user, week_start__lt=week_start)
        .order_by("-week_start")
        .first()
    )
    if tier is None:
        tier = (prev.difficulty_tier + 1) if prev else 1
    tier = max(1, min(10, int(tier)))

    WeeklyPlan.objects.filter(user=user, week_start=week_start).delete()

    plan = WeeklyPlan.objects.create(
        user=user,
        week_start=week_start,
        difficulty_tier=tier,
        assessment=assessment,
        source=source,
    )
    for row in build_week_days(assessment, tier):
        exercises = row.get("exercises") or []
        first = exercises[0] if exercises else {}
        day = WeeklyPlanDay.objects.create(
            plan=plan,
            day_index=int(row["day_index"]),
            is_rest=bool(row["is_rest"]),
            counter_profile_id=str(first.get("counter_profile_id") or ""),
            display_title=str(row.get("display_title") or ""),
            target_sets=int(first.get("target_sets") or 0),
            target_reps=int(first.get("target_reps") or 0),
            duration_sec=first.get("duration_sec"),
            focus_note=str(row.get("focus_note") or "")[:256],
            completed=False,
        )
        for ex in exercises:
            WeeklyPlanDayExercise.objects.create(
                day=day,
                sort_order=int(ex.get("sort_order") or 0),
                counter_profile_id=str(ex["counter_profile_id"]),
                display_title=str(ex.get("display_title") or ""),
                target_sets=int(ex.get("target_sets") or 3),
                target_reps=int(ex.get("target_reps") or 0),
                duration_sec=ex.get("duration_sec"),
                completed=False,
            )
    return plan


def ensure_weekly_plan_after_assessment(assessment: FitnessAssessment) -> WeeklyPlan | None:
    if not assessment.user_id:
        return None
    return replace_weekly_plan_for_user(
        assessment.user,
        assessment,
        week_start=monday_of(),
        tier=1,
        source="assessment",
    )


def simple_session_feedback(
    *,
    target_reps: int,
    target_sets: int,
    duration_target: int | None,
    reps: int,
    duration_sec: int,
    errors: list[Any],
    met_target: bool,
) -> str:
    if not met_target:
        if reps <= 0 and duration_sec <= 0:
            return "Сессия не засчитана: нет повторов или времени. Выполни хотя бы 60% от цели."
        return "Цель дня не достигнута. Добей объём или повтори упражнение позже."

    err_n = len(errors) if isinstance(errors, list) else 0
    base = "Упражнение выполнено — цель дня по этому блоку закрыта."
    if err_n > 0:
        base += f" Замечаний по технике: {err_n}."
    else:
        base += " Техника стабильная."
    return base
