from datetime import timedelta

from django.db.models import Count, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from main.models import Player, RunSession, WorkoutSession
from main.profile_helpers import workout_dates, workout_streak
from main.views.api_v1_helpers import WORKOUT_CATALOG, require_authenticated_json, serialize_workout


_NEXT_WORKOUT = {
    "PUSHUP": "squat_classic",
    "SQUAT": "crunch_classic",
    "CRUNCH": "pullup_classic",
    "PULLUP": "tabata_classic",
    "TABATA": "run_classic",
    "RUN": "pushup_classic",
}


def _catalog_by_id(workout_id: str):
    return next((item for item in WORKOUT_CATALOG if item["id"] == workout_id), WORKOUT_CATALOG[0])


def _daily_average(values: list[float]) -> float:
    if not values:
        return 0
    return sum(values) / len(values)


@require_GET
def api_v1_dashboard(request):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error

    player, _ = Player.objects.get_or_create(user=request.user)
    today = timezone.localdate()
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)

    today_sessions = WorkoutSession.objects.filter(player=player, date__gte=today_start)
    week_sessions = WorkoutSession.objects.filter(player=player, date__gte=week_start)
    today_totals = today_sessions.aggregate(
        calories=Sum("calories_burned"),
        duration=Sum("duration_seconds"),
        reps=Sum("reps_count"),
        count=Count("id"),
    )
    week_day_rows = (
        week_sessions.values("date__date")
        .annotate(calories=Sum("calories_burned"), duration=Sum("duration_seconds"))
        .order_by("date__date")
    )

    runs_today = RunSession.objects.filter(
        user=request.user, started_at__gte=today_start, status=RunSession.STATUS_FINISHED
    )
    runs_week = RunSession.objects.filter(
        user=request.user, started_at__gte=week_start, status=RunSession.STATUS_FINISHED
    )
    run_today = runs_today.aggregate(
        distance=Sum("distance_km"),
        calories=Sum("calories_estimate"),
        duration=Sum("duration_sec"),
    )
    run_week_rows = (
        runs_week.values("started_at__date")
        .annotate(
            distance=Sum("distance_km"),
            calories=Sum("calories_estimate"),
            duration=Sum("duration_sec"),
        )
        .order_by("started_at__date")
    )

    distance_km = float(run_today["distance"] or 0)
    calories_today = int((today_totals["calories"] or 0) + (run_today["calories"] or 0))
    active_minutes = int(((today_totals["duration"] or 0) + (run_today["duration"] or 0)) / 60)
    steps_today = int(distance_km * 1300) if distance_km else 0
    sessions_this_week = week_sessions.aggregate(count=Count("id"))["count"] or 0

    week_calories = [float(row["calories"] or 0) for row in week_day_rows]
    week_minutes = [int((row["duration"] or 0) / 60) for row in week_day_rows]
    week_steps = [int(float(row["distance"] or 0) * 1300) for row in run_week_rows]
    for row in run_week_rows:
        week_calories.append(float(row["calories"] or 0))
        week_minutes.append(int((row["duration"] or 0) / 60))

    calorie_goal = int(round(_daily_average([v for v in week_calories if v > 0]))) if any(week_calories) else 0
    steps_goal = int(round(_daily_average([v for v in week_steps if v > 0]))) if any(week_steps) else 0
    activity_goal = int(round(_daily_average([v for v in week_minutes if v > 0]))) if any(week_minutes) else 0

    last = WorkoutSession.objects.filter(player=player).order_by("-date").first()
    featured = _catalog_by_id(_NEXT_WORKOUT.get(last.exercise_type if last else "", "pushup_classic"))
    suggestion = serialize_workout(featured)
    suggestion = {
        "id": suggestion["id"],
        "title": suggestion["title"],
        "reason": "Следующая после последней тренировки" if last else "Начни с базовой тренировки",
        "durationMin": suggestion["durationMin"],
        "calories": suggestion["calories"],
    }

    recent = [
        {
            "id": str(s.id),
            "exercise": s.exercise_type,
            "reps": s.reps_count,
            "durationSec": s.duration_seconds,
            "calories": s.calories_burned,
            "date": s.date.isoformat(),
        }
        for s in WorkoutSession.objects.filter(player=player).order_by("-date")[:5]
    ]

    trained_days = sorted(
        d.isoformat()
        for d in workout_dates(player)
        if d >= (today - timedelta(days=6))
    )

    return JsonResponse(
        {
            "profile": {
                "username": request.user.username,
                "displayName": player.display_name or request.user.first_name or request.user.username,
                "avatarUrl": player.avatar_url or None,
                "telegramUsername": player.telegram_username or "",
                "level": player.level,
            },
            "metrics": {
                "caloriesToday": calories_today,
                "calorieGoal": calorie_goal,
                "stepsToday": steps_today,
                "stepsGoal": steps_goal,
                "activeMinutes": active_minutes,
                "activityGoal": activity_goal,
                "distanceKm": round(distance_km, 2),
                "sessionsThisWeek": sessions_this_week,
                "repsToday": int(today_totals["reps"] or 0),
                "workoutsToday": int(today_totals["count"] or 0),
                "workoutStreak": workout_streak(player, today),
                "workoutDatesThisWeek": trained_days,
            },
            "featuredWorkout": serialize_workout(_catalog_by_id("pushup_classic") if not last else featured),
            "aiSuggestion": suggestion,
            "recentWorkouts": recent,
        }
    )
