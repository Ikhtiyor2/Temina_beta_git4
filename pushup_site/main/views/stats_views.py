import logging
from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count

from ..models import WorkoutSession, WorkoutSet, Player

logger = logging.getLogger(__name__)

# ======================================================
# BASIC STATS
# ======================================================

@login_required
@require_GET
def get_basic_stats(request):
    """
    Базовая статистика пользователя.
    """

    try:
        player, _ = Player.objects.get_or_create(user=request.user)

        sessions = WorkoutSession.objects.filter(player=player)

        totals = sessions.aggregate(
            total_sessions=Count("id"),
            total_reps=Sum("reps_count"),
            total_time=Sum("duration_seconds"),
            total_calories=Sum("calories_burned"),
        )

        return JsonResponse({
            "success": True,
            "totals": {
                "sessions": totals["total_sessions"] or 0,
                "reps": totals["total_reps"] or 0,
                "time_seconds": totals["total_time"] or 0,
                "calories": totals["total_calories"] or 0,
            }
        })

    except Exception as e:
        logger.exception("Error getting basic stats")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# WORKOUT HISTORY
# ======================================================

@login_required
@require_GET
def get_workout_history(request):
    """
    Последние тренировки пользователя.
    """

    try:
        limit = min(max(int(request.GET.get("limit", 20)), 1), 100)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "invalid limit"}, status=400)

    player, _ = Player.objects.get_or_create(user=request.user)

    sessions = (
        WorkoutSession.objects
        .filter(player=player)
        .order_by("-date")[:limit]
    )

    data = []
    for s in sessions:
        data.append({
            "id": s.id,
            "exercise": s.exercise_type,
            "reps": s.reps_count,
            "duration": s.duration_seconds,
            "calories": s.calories_burned,
            "date": s.date.isoformat(),
        })

    return JsonResponse({
        "success": True,
        "history": data,
    })


# ======================================================
# DAILY ACTIVITY (FOR CHARTS)
# ======================================================

@login_required
@require_GET
def get_daily_activity(request):
    """
    Активность по дням (для графиков).
    """

    try:
        days = min(max(1, int(request.GET.get("days", 14))), 365)
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "invalid days"}, status=400)

    player, _ = Player.objects.get_or_create(user=request.user)

    since = timezone.now() - timedelta(days=days)

    sessions = (
        WorkoutSession.objects
        .filter(player=player, date__gte=since)
        .values("date__date")
        .annotate(
            reps=Sum("reps_count"),
            duration=Sum("duration_seconds"),
            calories=Sum("calories_burned"),
            workouts=Count("id"),
        )
        .order_by("date__date")
    )

    data = []
    for s in sessions:
        data.append({
            "date": s["date__date"].isoformat(),
            "reps": s["reps"] or 0,
            "duration": s["duration"] or 0,
            "calories": s["calories"] or 0,
            "workouts": s["workouts"] or 0,
        })

    return JsonResponse({
        "success": True,
        "days": data,
    })


# ======================================================
# EXERCISE BREAKDOWN
# ======================================================

@login_required
@require_GET
def get_exercise_breakdown(request):
    """
    Статистика по типам упражнений.
    """

    player = Player.objects.get(user=request.user)

    sessions = (
        WorkoutSession.objects
        .filter(player=player)
        .values("exercise_type")
        .annotate(
            reps=Sum("reps_count"),
            workouts=Count("id"),
            duration=Sum("duration_seconds"),
        )
        .order_by("-reps")
    )

    data = []
    for s in sessions:
        data.append({
            "exercise": s["exercise_type"],
            "reps": s["reps"] or 0,
            "workouts": s["workouts"] or 0,
            "duration": s["duration"] or 0,
        })

    return JsonResponse({
        "success": True,
        "breakdown": data,
    })
