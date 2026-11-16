import json
import math
from datetime import timedelta
from typing import Any

from django.db.models import Max
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from main.models import RunSession, RunTrackPoint, WorkoutSession

VALID_PERIODS = {"day", "week", "month", "all"}

# Max realistic single workout length (Tabata + warm-up + cool-down).
MAX_WORKOUT_DURATION_SECONDS = 4 * 60 * 60


def clamp_workout_duration_seconds(value, *, default: int = 0) -> int:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return default
    if seconds < 0:
        return default
    return min(seconds, MAX_WORKOUT_DURATION_SECONDS)


def active_workout_duration_seconds(workout) -> int:
    """
    Duration until the last camera frame, not until the save request.
    Prevents multi-day durations when an ActiveWorkout was left open.
    """
    if not workout or not getattr(workout, "start_time", None):
        return 0
    end = getattr(workout, "last_frame_time", None) or getattr(workout, "last_update", None) or timezone.now()
    start = workout.start_time
    if end < start:
        return 0
    return clamp_workout_duration_seconds(int((end - start).total_seconds()))

PUSHUP_IMAGE = "https://images.unsplash.com/photo-1598971639058-fab3c3109a00?auto=format&fit=crop&w=1200&q=85"
PULLUP_IMAGE = "https://images.unsplash.com/photo-1598266663439-2056e6900339?auto=format&fit=crop&w=1200&q=85"
SQUAT_IMAGE = "https://images.unsplash.com/photo-1532029837206-abbe2b7620e3?auto=format&fit=crop&w=1200&q=85"
CRUNCH_IMAGE = "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=1200&q=85"
PLANK_IMAGE = "https://images.unsplash.com/photo-1562771242-a02d9090c90c?auto=format&fit=crop&w=1200&q=85"


def _workout(
    workout_id: str,
    parent_type: str,
    title: str,
    subtitle: str,
    category: str,
    difficulty: str,
    image_url: str,
    duration_min: int,
    calories: int,
    reps: int,
    sets: int = 3,
    muscle_groups: list[str] | None = None,
    equipment: list[str] | None = None,
    supports_ai_counter: bool = True,
) -> dict[str, Any]:
    return {
        "id": workout_id,
        "parentType": parent_type,
        "aiExerciseType": parent_type,
        "title": title,
        "subtitle": subtitle,
        "category": category,
        "imageUrl": image_url,
        "durationMin": duration_min,
        "calories": calories,
        "difficulty": difficulty,
        "supportsAiCounter": supports_ai_counter,
        "counterProfile": parent_type,
        "muscleGroups": muscle_groups or [],
        "equipment": equipment or ["bodyweight"],
        "exercises": [
            {"id": parent_type, "title": title, "sets": sets, "reps": reps},
        ],
    }


TABATA_IMAGE = "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=1200&q=85"
RUN_IMAGE = "https://images.unsplash.com/photo-1476480862126-209bfaa8dba8?auto=format&fit=crop&w=1200&q=85"

WORKOUT_CATALOG: list[dict[str, Any]] = [
    _workout("pushup_classic", "PUSHUP", "Классические отжимания", "База для груди, плеч и трицепса", "Отжимания", "easy", PUSHUP_IMAGE, 12, 110, 12, muscle_groups=["chest", "triceps", "shoulders"]),
    _workout("pullup_classic", "PULLUP", "Классические подтягивания", "Спина, бицепс и хват", "Подтягивания", "medium", PULLUP_IMAGE, 15, 140, 6, muscle_groups=["back", "biceps"], equipment=["pullup_bar"]),
    _workout("squat_classic", "SQUAT", "Классические приседания", "Ноги и корпус", "Приседания", "easy", SQUAT_IMAGE, 15, 135, 15, muscle_groups=["legs", "glutes"]),
    _workout("crunch_classic", "CRUNCH", "Классические скручивания", "Пресс и контроль корпуса", "Пресс", "easy", CRUNCH_IMAGE, 12, 90, 16, muscle_groups=["abs"]),
    _workout("tabata_classic", "TABATA", "Табата", "Интервальная тренировка", "Табата", "medium", TABATA_IMAGE, 20, 180, 8, muscle_groups=["full_body"], supports_ai_counter=False),
    _workout("run_classic", "RUN", "Бег", "Кардио и выносливость", "Бег", "medium", RUN_IMAGE, 30, 250, 1, muscle_groups=["legs", "cardio"], supports_ai_counter=False),
]


def json_error(message: str, status: int = 400, code: str | None = None) -> JsonResponse:
    payload: dict[str, Any] = {"detail": message}
    if code:
        payload["code"] = code
    return JsonResponse(payload, status=status)


def parse_json_body(request) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    try:
        if not request.body:
            return {}, None
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, json_error("Invalid JSON body", status=400, code="invalid_json")
    if not isinstance(body, dict):
        return None, json_error("JSON body must be an object", status=400, code="invalid_body")
    return body, None


def require_authenticated_json(request) -> JsonResponse | None:
    if not request.user.is_authenticated:
        return json_error("Authentication required", status=401)
    return None


def request_lang(request) -> str:
    """Resolve UI language from ?lang= or Accept-Language (ru|en|uz)."""
    from main.locale_content import normalize_lang

    raw = (request.GET.get("lang") or "").strip()
    if not raw:
        accept = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").split(",")[0].strip()
        raw = accept
    return normalize_lang(raw)


def validate_period(period: str | None) -> tuple[str | None, JsonResponse | None]:
    value = period or "week"
    if value not in VALID_PERIODS:
        return None, json_error("Invalid period", status=400, code="invalid_period")
    return value, None


def get_workout(workout_id: str) -> dict[str, Any] | None:
    return next((w for w in WORKOUT_CATALOG if w["id"].lower() == workout_id.lower()), None)


def serialize_workout(workout: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": workout["id"],
        "title": workout["title"],
        "parentType": workout.get("parentType", ""),
        "aiExerciseType": workout.get("aiExerciseType", workout.get("counterProfile", "")),
        "subtitle": workout.get("subtitle", ""),
        "category": workout.get("category", workout.get("difficulty", "")),
        "imageUrl": workout["imageUrl"],
        "durationMin": workout["durationMin"],
        "calories": workout["calories"],
        "difficulty": workout["difficulty"],
        "supportsAiCounter": workout.get("supportsAiCounter", True),
        "counterProfile": workout.get("counterProfile", workout.get("aiExerciseType", "")),
        "muscleGroups": list(workout.get("muscleGroups", [])),
        "equipment": list(workout.get("equipment", [])),
        "exercises": list(workout["exercises"]),
    }


def serialize_workout_session(session: WorkoutSession, status: str = "started") -> dict[str, Any]:
    return {
        "sessionId": str(session.id),
        "workoutId": session.exercise_type,
        "status": status,
        "startedAt": session.date.isoformat(),
        "finishedAt": session.date.isoformat() if status == "finished" else None,
        "durationSec": int(session.duration_seconds or 0),
        "calories": float(session.calories_burned or 0),
        "reps": int(session.reps_count or 0),
    }


def serialize_run(run: RunSession, include_points: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "runId": str(run.id),
        "status": run.status,
        "startedAt": run.started_at.isoformat() if run.started_at else None,
        "pausedAt": run.paused_at.isoformat() if run.paused_at else None,
        "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
        "distanceKm": round(float(run.distance_km or 0), 3),
        "durationSec": int(run.duration_sec or 0),
        "paceMinPerKm": round(float(run.pace_min_per_km or 0), 2),
        "avgSpeed": round(float(run.avg_speed or 0), 2),
        "caloriesEstimate": round(float(run.calories_estimate or 0), 1),
    }
    if include_points:
        payload["points"] = [
            {
                "lat": p.lat,
                "lng": p.lng,
                "timestamp": p.timestamp.isoformat(),
                "accuracy": p.accuracy,
                "speedMps": p.speed_mps,
                "sequence": p.sequence,
            }
            for p in run.points.all().order_by("sequence", "timestamp", "id")
        ]
    return payload


def parse_point_timestamp(value: str | None):
    dt = parse_datetime(value or "")
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone=timezone.utc)
    return dt


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def next_run_sequence(run: RunSession) -> int:
    current = run.points.aggregate(max_sequence=Max("sequence"))["max_sequence"]
    return int(current or 0) + 1


def recalculate_run_metrics(run: RunSession) -> RunSession:
    points = list(run.points.all().order_by("sequence", "timestamp", "id"))
    distance_km = 0.0
    for prev, curr in zip(points, points[1:]):
        distance_km += haversine_km(prev.lat, prev.lng, curr.lat, curr.lng)

    if len(points) >= 2:
        duration_sec = max(0, int((points[-1].timestamp - points[0].timestamp).total_seconds()))
    else:
        end = run.finished_at or timezone.now()
        duration_sec = max(0, int((end - run.started_at).total_seconds()))

    distance_m = distance_km * 1000
    avg_speed = distance_m / duration_sec if duration_sec > 0 else 0
    pace_min_per_km = (duration_sec / 60) / distance_km if distance_km > 0 else 0

    run.distance_km = distance_km
    run.duration_sec = duration_sec
    run.avg_speed = avg_speed
    run.pace_min_per_km = pace_min_per_km
    run.calories_estimate = distance_km * 60
    run.save(
        update_fields=[
            "distance_km",
            "duration_sec",
            "avg_speed",
            "pace_min_per_km",
            "calories_estimate",
            "updated_at",
        ]
    )
    return run


def create_run_points(run: RunSession, raw_points: list[dict[str, Any]]) -> None:
    sequence = next_run_sequence(run)
    to_create = []
    for item in raw_points:
        if not isinstance(item, dict):
            raise ValueError("Each point must be an object")
        timestamp = parse_point_timestamp(item.get("timestamp"))
        if timestamp is None:
            raise ValueError("Point timestamp is invalid")
        to_create.append(
            RunTrackPoint(
                run_session=run,
                lat=float(item["lat"]),
                lng=float(item["lng"]),
                timestamp=timestamp,
                accuracy=float(item["accuracy"]) if item.get("accuracy") is not None else None,
                speed_mps=float(item["speedMps"]) if item.get("speedMps") is not None else None,
                sequence=sequence,
            )
        )
        sequence += 1
    if to_create:
        RunTrackPoint.objects.bulk_create(to_create)


def period_start(period: str):
    now = timezone.now()
    if period == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start = now - timedelta(days=6)
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        start = now - timedelta(days=29)
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    return None


def period_dates(period: str, dates_from_data: list | None = None) -> list:
    start = period_start(period)
    if period == "day":
        return [timezone.localdate()]
    if period in {"week", "month"}:
        days = 7 if period == "week" else 30
        start_date = timezone.localdate() - timedelta(days=days - 1)
        return [start_date + timedelta(days=i) for i in range(days)]
    return dates_from_data or [timezone.localdate()]
