from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from main.models import RunSession, Player
from main.views.api_v1_helpers import (
    create_run_points,
    json_error,
    parse_json_body,
    recalculate_run_metrics,
    require_authenticated_json,
    serialize_run,
)
from main.workout_completion import finalize_workout


MAX_RUN_POINTS_PER_REQUEST = 500


@require_POST
def api_v1_run_start(request):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    run = RunSession.objects.create(user=request.user, status=RunSession.STATUS_RUNNING)
    return JsonResponse(serialize_run(run), status=201)


@require_http_methods(["PATCH"])
def api_v1_run_track(request, run_id: int):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    run = _get_run_or_error(request, run_id)
    if isinstance(run, JsonResponse):
        return run
    if run.status != RunSession.STATUS_RUNNING:
        return json_error("Run tracking is allowed only while running", status=400, code="run_not_running")

    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None
    points = body.get("points")
    if not isinstance(points, list):
        return json_error("points must be an array", status=400, code="invalid_points")
    if len(points) > MAX_RUN_POINTS_PER_REQUEST:
        return json_error(
            f"At most {MAX_RUN_POINTS_PER_REQUEST} points per request",
            status=400,
            code="too_many_points",
        )

    try:
        create_run_points(run, points)
    except (KeyError, TypeError, ValueError) as e:
        return json_error(str(e), status=400, code="invalid_points")

    run = recalculate_run_metrics(run)
    return JsonResponse(serialize_run(run, include_points=True))


@require_POST
def api_v1_run_pause(request, run_id: int):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    run = _get_run_or_error(request, run_id)
    if isinstance(run, JsonResponse):
        return run
    if run.status != RunSession.STATUS_RUNNING:
        return json_error("Only running sessions can be paused", status=400, code="invalid_status")
    run.status = RunSession.STATUS_PAUSED
    run.paused_at = timezone.now()
    run.save(update_fields=["status", "paused_at", "updated_at"])
    return JsonResponse(serialize_run(run))


@require_POST
def api_v1_run_resume(request, run_id: int):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    run = _get_run_or_error(request, run_id)
    if isinstance(run, JsonResponse):
        return run
    if run.status != RunSession.STATUS_PAUSED:
        return json_error("Only paused sessions can be resumed", status=400, code="invalid_status")
    run.status = RunSession.STATUS_RUNNING
    run.paused_at = None
    run.save(update_fields=["status", "paused_at", "updated_at"])
    return JsonResponse(serialize_run(run))


@require_POST
def api_v1_run_finish(request, run_id: int):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    run = _get_run_or_error(request, run_id)
    if isinstance(run, JsonResponse):
        return run
    if run.status == RunSession.STATUS_FINISHED:
        return JsonResponse(serialize_run(run, include_points=True))
    if run.status not in {RunSession.STATUS_RUNNING, RunSession.STATUS_PAUSED}:
        return json_error("Run cannot be finished from current status", status=400, code="invalid_status")
    run.status = RunSession.STATUS_FINISHED
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "finished_at", "updated_at"])
    run = recalculate_run_metrics(run)

    player, _ = Player.objects.get_or_create(user=request.user)
    distance_m = int(float(run.distance_km or 0) * 1000)
    result = finalize_workout(
        player,
        exercise_type="RUN",
        reps=distance_m,
        duration_sec=int(run.duration_sec or 0),
        calories=float(run.calories_estimate or 0),
        integrity={"distance_km": float(run.distance_km or 0)},
        user=request.user,
    )
    payload = serialize_run(run, include_points=True)
    payload["xpEarned"] = result["xp_earned"]
    payload["leveledUp"] = result["leveled_up"]
    return JsonResponse(payload)


@require_GET
def api_v1_run_detail(request, run_id: int):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    run = _get_run_or_error(request, run_id)
    if isinstance(run, JsonResponse):
        return run
    return JsonResponse(serialize_run(run, include_points=True))


@require_GET
def api_v1_run_history(request):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    try:
        limit = min(max(int(request.GET.get("limit", 20)), 1), 100)
    except (TypeError, ValueError):
        return json_error("Invalid limit parameter", status=400, code="invalid_parameter")
    runs = RunSession.objects.filter(user=request.user).order_by("-started_at")[:limit]
    return JsonResponse({"runs": [serialize_run(run) for run in runs]})


def _get_run_or_error(request, run_id: int):
    try:
        return RunSession.objects.get(id=run_id, user=request.user)
    except RunSession.DoesNotExist:
        return json_error("Run not found", status=404, code="run_not_found")
