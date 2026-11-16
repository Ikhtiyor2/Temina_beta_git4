from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from main.integrity import sanitize_client_reps
from main.models import Player, WorkoutSession
from main.views.api_v1_helpers import (
    WORKOUT_CATALOG,
    clamp_workout_duration_seconds,
    get_workout,
    json_error,
    parse_json_body,
    require_authenticated_json,
    serialize_workout,
    serialize_workout_session,
)
from main.workout_completion import finalize_workout, normalize_exercise_type


@require_GET
def api_v1_workouts(request):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    return JsonResponse({"workouts": [serialize_workout(w) for w in WORKOUT_CATALOG]})


@require_GET
def api_v1_workout_detail(request, workout_id: str):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    workout = get_workout(workout_id)
    if not workout:
        return json_error("Workout not found", status=404, code="workout_not_found")
    return JsonResponse(serialize_workout(workout))


@require_POST
def api_v1_workout_start(request, workout_id: str):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    workout = get_workout(workout_id)
    if not workout:
        return json_error("Workout not found", status=404, code="workout_not_found")

    player, _ = Player.objects.get_or_create(user=request.user)
    exercise_type = normalize_exercise_type(
        workout.get("parentType") or workout.get("aiExerciseType") or workout_id
    )
    session = WorkoutSession.objects.create(
        player=player,
        exercise_type=exercise_type,
        reps_count=0,
        duration_seconds=0,
        calories_burned=0,
        errors_count=0,
    )
    return JsonResponse(serialize_workout_session(session, status="started"), status=201)


@require_POST
def api_v1_workout_session_finish(request, session_id: int):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None

    player, _ = Player.objects.get_or_create(user=request.user)
    try:
        session = WorkoutSession.objects.get(id=session_id, player=player)
    except WorkoutSession.DoesNotExist:
        return json_error("Workout session not found", status=404, code="session_not_found")

    duration_sec = clamp_workout_duration_seconds(body.get("durationSec") or body.get("duration_sec") or 0)
    calories = float(body.get("calories") or 0)
    integrity = body.get("integrity") or {}
    errors_count = int(body.get("errorsCount") or 0)
    if isinstance(integrity, dict) and not errors_count:
        errors_count = int(integrity.get("critical_violations") or 0)
    exercises = body.get("exercises") or []
    if not isinstance(exercises, list):
        return json_error("exercises must be an array", status=400, code="invalid_exercises")

    exercise_type = normalize_exercise_type(session.exercise_type)
    total_reps = 0
    for item in exercises:
        if not isinstance(item, dict):
            return json_error("Each exercise result must be an object", status=400, code="invalid_exercises")
        reps = int(item.get("reps") or 0)
        exercise_id = str(item.get("exerciseId") or "").upper()
        if exercise_id:
            exercise_type = normalize_exercise_type(exercise_id)
        reps = sanitize_client_reps(
            reps,
            integrity=integrity if isinstance(integrity, dict) else None,
        )
        total_reps += reps

    if not exercises:
        total_reps = sanitize_client_reps(
            int(body.get("reps") or session.reps_count or 0),
            integrity=integrity if isinstance(integrity, dict) else None,
        )

    result = finalize_workout(
        player,
        exercise_type=exercise_type,
        reps=total_reps,
        duration_sec=duration_sec,
        calories=calories if calories > 0 else None,
        errors_count=errors_count,
        integrity=integrity if isinstance(integrity, dict) else None,
        user=request.user,
        existing_session=session,
    )

    payload = serialize_workout_session(session, status="finished")
    payload["exercises"] = exercises
    payload["xpEarned"] = result["xp_earned"]
    payload["xpGained"] = result["xp_earned"]
    payload["leveledUp"] = result["leveled_up"]
    payload["questsCompleted"] = result["quests_completed"]
    return JsonResponse(payload)
