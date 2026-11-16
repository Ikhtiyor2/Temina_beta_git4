from __future__ import annotations

from datetime import timedelta
from collections import defaultdict

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from main.models import Player, WorkoutSession, ActiveWorkout


# =============================================================================
# HUD — SINGLE SOURCE OF TRUTH (AI detector state)
# =============================================================================

@login_required
@require_GET
def get_hud_state(request):
    """
    ЕДИНСТВЕННЫЙ источник данных для HUD.
    Никакой бизнес-логики — только состояние детектора из session.
    """

    exercise_type = request.GET.get("exercise", "PUSHUP")
    player, _ = Player.objects.get_or_create(user=request.user)
    workout = (
        ActiveWorkout.objects.filter(
            player=player,
            exercise_type=exercise_type,
            is_active=True,
        )
        .order_by("-last_update")
        .first()
    )

    if workout:
        count = int(workout.count or 0)
        stage = workout.stage or "up"
        ready = bool(workout.ready)
        start_time = workout.start_time.timestamp() if workout.start_time else None
        session_start_time = start_time
    else:
        detector_key = f"detector:{request.user.id}:{exercise_type}"
        state = request.session.get(detector_key, {})
        count = int(state.get("count", 0) or 0)
        stage = state.get("stage", "up") or "up"
        ready = bool(state.get("ready", False))
        start_time = state.get("start_time")
        session_start_time = state.get("session_start_time")

    workout_duration = 0
    if start_time:
        try:
            workout_duration = int(timezone.now().timestamp() - float(start_time))
        except Exception:
            workout_duration = 0

    return JsonResponse({
        "success": True,
        "exercise": exercise_type,

        # core
        "count": count,
        "reps": count,
        "stage": stage,
        "ready": ready,

        # time
        "workout_duration": workout_duration,

        # placeholders (совместимость)
        "quality": 100 if ready else 0,
        "errors": 0,
        "xp_gained": 0,
        "calories_burned": 0,

        # meta
        "server_time": timezone.now().isoformat(),
    })


# =============================================================================
# HUD ALIASES (BACKWARD COMPATIBILITY)
# =============================================================================

get_real_time_hud_data = get_hud_state
get_unified_hud_data = get_hud_state
get_hud_data = get_hud_state


# =============================================================================
# STATS — HELPERS
# =============================================================================

def _safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


def _start_of_day(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _exercise_key_from_type(exercise_type: str) -> str:
    """
    Приводим тип упражнения к ключам, которые ожидает stats.html:
    pushups, squats, crunches, pullups
    """
    t = (exercise_type or "").lower()

    # частые варианты
    if "push" in t:
        return "pushups"
    if "squat" in t:
        return "squats"
    if "crunch" in t or "abs" in t:
        return "crunches"
    if "pull" in t:
        return "pullups"
    if "plank" in t:
        return "planks"

    # если хранится как PUSHUP / SQUAT и тд
    if t in ("pushup", "pushups"):
        return "pushups"
    if t in ("squat", "squats"):
        return "squats"
    if t in ("crunch", "crunches"):
        return "crunches"
    if t in ("pullup", "pullups"):
        return "pullups"
    if t in ("plank", "planks"):
        return "planks"

    # fallback
    return "pushups"


def _default_payload():
    """
    Возвращает пустой валидный формат для stats.html.
    """
    return {
        "success": True,

        "basicStats": {
            "total_stats": {
                "total_workouts": 0,
                "total_reps": 0,
                "total_calories": 0,
                "current_streak": 0,
                "max_streak": 0,
            },
            "today_stats": {
                "today_workouts": 0,
                "today_reps": 0,
                "today_calories": 0,
            },
        },

        "compStats": {
            "player": {"level": 1, "exp": 0, "exp_to_level": 100},
            "xp_progress": {"current": 0, "max": 100},
            "exercise_stats": {
                "pushups": {"total": 0, "max_single": 0, "progress": 0},
                "squats": {"total": 0, "max_single": 0, "progress": 0},
                "crunches": {"total": 0, "max_single": 0, "progress": 0},
                "pullups": {"total": 0, "max_single": 0, "progress": 0},
                "planks": {"total": 0, "max_single": 0, "progress": 0},
            },
            "achievements": [],
        },

        "timeStats": {
            "time_stats": {
                "total_time": {"hours": 0, "minutes": 0},
                "workout_time": {"hours": 0, "minutes": 0},
                "efficiency": 0,
                "intensity": 0,
                "current_session": {"minutes": 0},
                "today": {"workout_minutes": 0, "goal": 30, "progress": 0},
                "week": {"workout_minutes": 0, "goal": 150, "progress": 0, "daily_intensity": [0, 0, 0, 0, 0, 0, 0]},
            }
        },

        "weekly_intensity": [0, 0, 0, 0, 0, 0, 0],
    }


# =============================================================================
# STATS — COMBINED ENDPOINT
# =============================================================================

@login_required
@require_GET
def api_stats_combined(request):
    """
    Единый endpoint для stats.html.

    Гарантии:
    - НЕ импортит api_stats_basic и тд (их нет).
    - НЕ ломается, если Player отсутствует.
    - Возвращает формат, который ожидает stats.html.
    """

    user = request.user
    now = timezone.now()
    today_start = _start_of_day(now)

    # -------------------------------------------------------------------------
    # Player
    # -------------------------------------------------------------------------
    player = Player.objects.filter(user=user).first()
    if not player:
        # игрок не создан — отдаем пустой формат, UI не падает
        return JsonResponse(_default_payload())

    # -------------------------------------------------------------------------
    # Sessions
    # -------------------------------------------------------------------------
    sessions = WorkoutSession.objects.filter(player=player).order_by("-date")

    # totals
    total_workouts = sessions.count()
    total_reps = 0
    total_calories = 0
    total_duration_seconds = 0

    # today
    today_sessions = sessions.filter(date__gte=today_start)
    today_workouts = today_sessions.count()
    today_reps = 0
    today_calories = 0
    today_duration_seconds = 0

    # exercise stats
    exercise_totals = defaultdict(int)
    exercise_best = defaultdict(int)

    # weekly intensity (last 7 days)
    # делаем массив: Пн..Вс
    # intensity = workout_minutes / goal_minutes * 100 (ограничим 0..100)
    weekly_goal_minutes = 150
    daily_goal_minutes = 30

    # даты 7 дней назад включая сегодня
    start_7 = today_start - timedelta(days=6)
    last_7_sessions = sessions.filter(date__gte=start_7)

    # минуты по дням
    minutes_by_day = defaultdict(int)

    for s in sessions:
        reps = _safe_int(getattr(s, "reps_count", 0), 0)
        cal = _safe_int(getattr(s, "calories_burned", 0), 0)
        dur = _safe_int(getattr(s, "duration_seconds", 0), 0)

        total_reps += reps
        total_calories += cal
        total_duration_seconds += dur

        ex_key = _exercise_key_from_type(getattr(s, "exercise_type", "pushups"))
        exercise_totals[ex_key] += reps
        exercise_best[ex_key] = max(exercise_best[ex_key], reps)

    for s in today_sessions:
        reps = _safe_int(getattr(s, "reps_count", 0), 0)
        cal = _safe_int(getattr(s, "calories_burned", 0), 0)
        dur = _safe_int(getattr(s, "duration_seconds", 0), 0)

        today_reps += reps
        today_calories += cal
        today_duration_seconds += dur

    for s in last_7_sessions:
        day = _start_of_day(s.date)
        dur = _safe_int(getattr(s, "duration_seconds", 0), 0)
        minutes_by_day[day] += int(dur // 60)

    # -------------------------------------------------------------------------
    # Streak
    # -------------------------------------------------------------------------
    # Серия = количество дней подряд, когда есть хотя бы 1 тренировка.
    # Максимум считаем по всем дням.
    workout_days = set(
        sessions.values_list("date", flat=True)
    )

    # workout_days содержит datetime — приводим к date
    workout_dates = sorted({d.date() for d in workout_days if d})

    # current streak
    current_streak = 0
    cursor = now.date()

    workout_dates_set = set(workout_dates)
    while cursor in workout_dates_set:
        current_streak += 1
        cursor -= timedelta(days=1)

    # max streak
    max_streak = 0
    tmp = 0
    prev = None
    for d in workout_dates:
        if prev is None:
            tmp = 1
        else:
            if d == prev + timedelta(days=1):
                tmp += 1
            else:
                tmp = 1
        prev = d
        max_streak = max(max_streak, tmp)

    # -------------------------------------------------------------------------
    # Time stats
    # -------------------------------------------------------------------------
    total_minutes = int(total_duration_seconds // 60)
    workout_minutes = total_minutes  # в проекте нет "не workout" времени, поэтому так

    today_minutes = int(today_duration_seconds // 60)

    # weekly minutes
    week_minutes = sum(minutes_by_day.values())

    # efficiency: условно, если есть duration, то 100, иначе 0 (можно улучшить позже)
    efficiency = 0
    if total_duration_seconds > 0:
        efficiency = min(100, max(10, int((total_reps / max(1, total_workouts)))))  # мягкая метрика

    # intensity today: today_minutes / daily_goal * 100
    intensity_today = 0
    if daily_goal_minutes > 0:
        intensity_today = int(min(100, round((today_minutes / daily_goal_minutes) * 100)))

    # weekly intensity array (Mon..Sun)
    # Берем последние 7 дней и переводим в проценты от daily_goal_minutes
    daily_intensity = []
    for i in range(6, -1, -1):
        day = (today_start - timedelta(days=i)).date()
        # minutes_by_day ключ = datetime start_of_day
        day_dt = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        mins = minutes_by_day.get(day_dt, 0)
        if daily_goal_minutes > 0:
            pct = int(min(100, round((mins / daily_goal_minutes) * 100)))
        else:
            pct = 0
        daily_intensity.append(pct)

    # weekly progress percent
    weekly_progress = 0
    if weekly_goal_minutes > 0:
        weekly_progress = int(round((week_minutes / weekly_goal_minutes) * 100))

    # daily progress percent
    daily_progress = 0
    if daily_goal_minutes > 0:
        daily_progress = int(round((today_minutes / daily_goal_minutes) * 100))

    # -------------------------------------------------------------------------
    # Player / XP
    # -------------------------------------------------------------------------
    level = _safe_int(getattr(player, "level", 1), 1)
    exp = _safe_int(getattr(player, "exp", 0), 0)

    # exp_to_level может называться иначе
    exp_to_level = getattr(player, "exp_to_level", None)
    if exp_to_level is None:
        exp_to_level = getattr(player, "exp_to_next_level", None)
    exp_to_level = _safe_int(exp_to_level, 100)

    # -------------------------------------------------------------------------
    # Exercise stats payload
    # -------------------------------------------------------------------------
    # progress = total / max(total across exercises) * 100
    # (так будет логично и стабильно)
    max_total_any = max([exercise_totals.get(k, 0) for k in ["pushups", "squats", "crunches", "pullups", "planks"]] + [1])

    def ex_payload(key):
        total = exercise_totals.get(key, 0)
        best = exercise_best.get(key, 0)
        progress = int(round((total / max_total_any) * 100)) if max_total_any > 0 else 0
        return {
            "total": int(total),
            "max_single": int(best),
            "progress": int(max(0, min(100, progress))),
        }

    exercise_stats = {
        "pushups": ex_payload("pushups"),
        "squats": ex_payload("squats"),
        "crunches": ex_payload("crunches"),
        "pullups": ex_payload("pullups"),
        "planks": ex_payload("planks"),
    }

    # -------------------------------------------------------------------------
    # Achievements (пока простые, безопасные)
    # -------------------------------------------------------------------------
    # Чтобы UI не был пустым, но и не ломал бизнес-логику.
    achievements = []

    def add_ach(name, description, icon, unlocked, progress=0, requirement=100):
        achievements.append({
            "name": name,
            "description": description,
            "icon": icon,
            "unlocked": bool(unlocked),
            "progress": int(progress),
            "requirement": int(requirement),
        })

    # 1) Первая тренировка
    add_ach(
        "Первый шаг",
        "Сделайте первую тренировку.",
        "ri-rocket-line",
        unlocked=(total_workouts >= 1),
        progress=min(100, int(total_workouts * 100)),
        requirement=1
    )

    # 2) Серия 3
    add_ach(
        "Упорный",
        "Тренируйтесь 3 дня подряд.",
        "ri-fire-line",
        unlocked=(max_streak >= 3),
        progress=min(100, int((max_streak / 3) * 100)),
        requirement=3
    )

    # 3) 1000 повторений
    add_ach(
        "Машина",
        "Сделайте 1000 повторений.",
        "ri-flashlight-line",
        unlocked=(total_reps >= 1000),
        progress=min(100, int((total_reps / 1000) * 100)),
        requirement=1000
    )

    # 4) 10 тренировок
    add_ach(
        "Стабильность",
        "Выполните 10 тренировок.",
        "ri-checkbox-circle-line",
        unlocked=(total_workouts >= 10),
        progress=min(100, int((total_workouts / 10) * 100)),
        requirement=10
    )

    # -------------------------------------------------------------------------
    # Final payload
    # -------------------------------------------------------------------------
    payload = {
        "success": True,

        "basicStats": {
            "total_stats": {
                "total_workouts": int(total_workouts),
                "total_reps": int(total_reps),
                "total_calories": int(total_calories),
                "current_streak": int(current_streak),
                "max_streak": int(max_streak),
            },
            "today_stats": {
                "today_workouts": int(today_workouts),
                "today_reps": int(today_reps),
                "today_calories": int(today_calories),
            },
        },

        "compStats": {
            "player": {
                "level": int(level),
                "exp": int(exp),
                "exp_to_level": int(exp_to_level),
            },
            "xp_progress": {
                "current": int(exp),
                "max": int(exp_to_level),
            },
            "exercise_stats": exercise_stats,
            "achievements": achievements,
        },

        "timeStats": {
            "time_stats": {
                "total_time": {"hours": int(total_minutes // 60), "minutes": int(total_minutes % 60)},
                "workout_time": {"hours": int(workout_minutes // 60), "minutes": int(workout_minutes % 60)},
                "efficiency": int(max(0, min(100, efficiency))),
                "intensity": int(max(0, min(100, intensity_today))),
                "current_session": {"minutes": int(today_minutes)},
                "today": {
                    "workout_minutes": int(today_minutes),
                    "goal": int(daily_goal_minutes),
                    "progress": int(daily_progress),
                },
                "week": {
                    "workout_minutes": int(week_minutes),
                    "goal": int(weekly_goal_minutes),
                    "progress": int(weekly_progress),
                    "daily_intensity": daily_intensity,
                },
            }
        },

        "weekly_intensity": daily_intensity,
    }

    return JsonResponse(payload)
