from collections import defaultdict

from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from main.models import Player, RunSession, WorkoutSession
from main.views.api_v1_helpers import (
    period_dates,
    period_start,
    require_authenticated_json,
    validate_period,
)


@require_GET
def api_v1_stats_calories(request):
    return _stats_response(request, metric="calories")


@require_GET
def api_v1_stats_steps(request):
    return _stats_response(request, metric="steps")


@require_GET
def api_v1_stats_activity(request):
    return _stats_response(request, metric="activity")


@require_GET
def api_v1_stats_calories_breakdown(request):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error

    period, period_error = validate_period(request.GET.get("period"))
    if period_error:
        return period_error
    assert period is not None

    player, _ = Player.objects.get_or_create(user=request.user)
    start = period_start(period)
    session_qs = WorkoutSession.objects.filter(player=player)
    run_qs = RunSession.objects.filter(user=request.user)
    if start is not None:
        session_qs = session_qs.filter(date__gte=start)
        run_qs = run_qs.filter(started_at__gte=start)

    exercise = float(session_qs.aggregate(total=Sum("calories_burned"))["total"] or 0)
    runs = float(run_qs.aggregate(total=Sum("calories_estimate"))["total"] or 0)
    items = []
    if exercise > 0:
        items.append({"label": "Exercise", "value": round(exercise, 2)})
    if runs > 0:
        items.append({"label": "Runs", "value": round(runs, 2)})
    return JsonResponse({"period": period, "total": round(exercise + runs, 2), "items": items})


def _stats_response(request, metric: str):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error

    period, period_error = validate_period(request.GET.get("period"))
    if period_error:
        return period_error
    assert period is not None

    player, _ = Player.objects.get_or_create(user=request.user)
    start = period_start(period)
    session_qs = WorkoutSession.objects.filter(player=player)
    run_qs = RunSession.objects.filter(user=request.user)
    if start is not None:
        session_qs = session_qs.filter(date__gte=start)
        run_qs = run_qs.filter(started_at__gte=start)

    values_by_date = defaultdict(float)
    if metric in {"calories", "activity"}:
        workout_rows = (
            session_qs.values("date__date")
            .annotate(
                calories=Sum("calories_burned"),
                duration=Sum("duration_seconds"),
            )
            .order_by("date__date")
        )
        for row in workout_rows:
            date = row["date__date"]
            if metric == "calories":
                values_by_date[date] += float(row["calories"] or 0)
            else:
                values_by_date[date] += int((row["duration"] or 0) / 60)
        run_rows = (
            run_qs.values("started_at__date")
            .annotate(
                calories=Sum("calories_estimate"),
                duration=Sum("duration_sec"),
            )
            .order_by("started_at__date")
        )
        for row in run_rows:
            date = row["started_at__date"]
            if metric == "calories":
                values_by_date[date] += float(row["calories"] or 0)
            else:
                values_by_date[date] += int((row["duration"] or 0) / 60)
    else:
        rows = run_qs.values("started_at__date").annotate(distance=Sum("distance_km")).order_by("started_at__date")
        for row in rows:
            values_by_date[row["started_at__date"]] += int(float(row["distance"] or 0) * 1300)

    data_dates = sorted(values_by_date.keys())
    dates = period_dates(period, data_dates)
    points = [
        {
            "label": _label_for_date(d, period),
            "date": d.isoformat(),
            "value": round(values_by_date.get(d, 0), 2),
        }
        for d in dates
    ]
    active = [point["value"] for point in points if point["value"] > 0]
    goal = int(round(sum(active) / len(active))) if active else 0
    return JsonResponse(
        {
            "period": period,
            "unit": _unit_for_metric(metric),
            "total": round(sum(point["value"] for point in points), 2),
            "goal": goal,
            "points": points,
        }
    )


def _unit_for_metric(metric: str) -> str:
    if metric == "calories":
        return "kcal"
    if metric == "steps":
        return "steps"
    return "min"


def _label_for_date(date, period: str) -> str:
    if period == "week":
        return date.strftime("%a")
    if period == "month":
        return date.strftime("%d %b")
    if period == "all":
        return date.strftime("%Y-%m-%d")
    if date == timezone.localdate():
        return "Today"
    return date.strftime("%d %b")
