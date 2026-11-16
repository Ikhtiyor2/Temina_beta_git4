"""
Native assessment API: POST /api/v1/users/me/assessment/
Accepts the Android schemaVersion=1 questionnaire payload.
"""
import json
import logging
from typing import Any

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from main.models import FitnessAssessment

logger = logging.getLogger(__name__)

ALLOWED_GENDER = {"male", "female", "other", "prefer_not_to_say"}
ALLOWED_SLEEP_QUALITY = {"excellent", "great", "ok", "poor", "insomnia"}
ALLOWED_SLEEP_BANDS = {"gte_8", "7_8", "6_7", "lt_6", "unknown"}
ALLOWED_PRIMARY_GOALS = {
    "lose_weight",
    "gain_muscle",
    "maintain",
    "health",
    "endurance",
    "flexibility",
    "other",
}
ALLOWED_EQUIPMENT = {
    "none",
    "dumbbells",
    "barbell",
    "bands",
    "gym_access",
    "pullup_bar",
    "kettlebell",
    "cardio_machine",
    "bench",
    "cable_machine",
}
ALLOWED_HEALTH_SLUGS = {
    "none",
    "knee",
    "back",
    "shoulders",
    "hips",
    "heart",
    "pregnancy",
    "hypertension",
    "diabetes",
    "asthma",
}
SESSION_MINUTES = {15, 30, 45, 60}


def _err(field: str, code: str, message: str) -> dict[str, Any]:
    return {"field": field, "code": code, "message": message}


def _float_range(data: dict, field: str, min_v: float, max_v: float, required_msg: str, range_msg: str) -> tuple[float | None, list]:
    if data.get(field) is None:
        return None, [_err(field, "required", required_msg)]
    try:
        value = float(data.get(field))
    except (TypeError, ValueError):
        return None, [_err(field, "invalid", "Некорректное значение")]
    if not min_v <= value <= max_v:
        return value, [_err(field, "range", range_msg)]
    return value, []


def _list_field(data: dict, field: str, allowed: set[str], required: bool = False) -> tuple[list[str], list]:
    value = data.get(field) or []
    if not isinstance(value, list):
        return [], [_err(field, "invalid", "Ожидается массив")]
    if required and not value:
        return [], [_err(field, "required", "Выбери значение")]
    for item in value:
        if item not in allowed:
            return value, [_err(field, "invalid_slug", f"Неизвестное значение: {item}")]
    return value, []


def validate_assessment_body(data: dict) -> tuple[dict[str, Any] | None, list]:
    field_errors: list = []
    warnings: list[str] = []

    if data.get("schemaVersion") != 1:
        return None, [_err("schemaVersion", "invalid", "Ожидается schemaVersion: 1")]

    gender = data.get("gender")
    if gender not in ALLOWED_GENDER:
        field_errors.append(_err("gender", "invalid", "Некорректное значение gender"))

    try:
        age = int(data.get("ageYears"))
        if not 13 <= age <= 120:
            raise ValueError
    except (TypeError, ValueError):
        field_errors.append(_err("ageYears", "range", "Возраст 13–120"))
        age = None

    height_cm, h_errs = _float_range(data, "heightCm", 100, 250, "Укажи рост в см", "Рост должен быть 100–250 см")
    weight_kg, w_errs = _float_range(data, "weightKg", 30, 300, "Укажи вес", "Вес 30–300 кг")
    field_errors.extend(h_errs)
    field_errors.extend(w_errs)

    if "hasTrainingExperience" not in data or not isinstance(data["hasTrainingExperience"], bool):
        field_errors.append(_err("hasTrainingExperience", "required", "Укажи опыт тренировок"))

    try:
        fitness_level = int(data.get("fitnessLevel"))
        if not 1 <= fitness_level <= 5:
            raise ValueError
    except (TypeError, ValueError):
        field_errors.append(_err("fitnessLevel", "range", "Уровень 1–5"))
        fitness_level = None

    if data.get("sleepQuality") not in ALLOWED_SLEEP_QUALITY:
        field_errors.append(_err("sleepQuality", "invalid", "Некорректное качество сна"))

    if data.get("sleepHoursBand", "unknown") not in ALLOWED_SLEEP_BANDS:
        field_errors.append(_err("sleepHoursBand", "invalid", "Некорректный диапазон сна"))

    health, health_errs = _list_field(data, "healthLimitations", ALLOWED_HEALTH_SLUGS)
    equipment, eq_errs = _list_field(data, "availableEquipment", ALLOWED_EQUIPMENT, required=True)
    field_errors.extend(health_errs)
    field_errors.extend(eq_errs)

    if len(health) > 10:
        field_errors.append(_err("healthLimitations", "max", "Не более 10 пунктов"))

    for note_field in ("customLimitationNote", "chronicConditionsNote"):
        note = data.get(note_field)
        if note is not None and note is not None and not isinstance(note, str):
            field_errors.append(_err(note_field, "invalid", "Ожидается строка"))
        if isinstance(note, str) and len(note) > 500:
            field_errors.append(_err(note_field, "max", "Не более 500 символов"))

    if "hasChronicConditions" not in data or not isinstance(data["hasChronicConditions"], bool):
        field_errors.append(_err("hasChronicConditions", "required", "Ответь на вопрос о хронических заболеваниях"))

    primary_goal = data.get("primaryGoal")
    if primary_goal not in ALLOWED_PRIMARY_GOALS:
        field_errors.append(_err("primaryGoal", "invalid", "Некорректная цель"))

    try:
        workouts_per_week = int(data.get("workoutsPerWeek"))
        if not 1 <= workouts_per_week <= 7:
            raise ValueError
    except (TypeError, ValueError):
        field_errors.append(_err("workoutsPerWeek", "range", "1–7 дней"))
        workouts_per_week = None

    try:
        session_minutes = int(data.get("preferredSessionMinutes"))
        if session_minutes not in SESSION_MINUTES:
            raise ValueError
    except (TypeError, ValueError):
        field_errors.append(_err("preferredSessionMinutes", "invalid", "15, 30, 45 или 60"))
        session_minutes = None

    if "bodyScanConsent" not in data or not isinstance(data["bodyScanConsent"], bool):
        field_errors.append(_err("bodyScanConsent", "required", "Нужно согласие на скан"))
    if "bodyScanSkipped" not in data or not isinstance(data["bodyScanSkipped"], bool):
        field_errors.append(_err("bodyScanSkipped", "required", "Укажи пропуск скана"))
    if data.get("assessmentConfirmed") is not True:
        field_errors.append(_err("assessmentConfirmed", "required", "Подтверди анкету"))

    if data.get("hasChronicConditions"):
        warnings.append("medical_disclaimer")
    if health and "none" not in health and len(health) >= 3:
        warnings.append("low_activity_recommendation")

    if field_errors:
        return None, field_errors

    return {
        "gender": gender,
        "age_years": age,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "primary_goal": primary_goal,
        "fitness_level": fitness_level,
        "workouts_per_week": workouts_per_week,
        "preferred_session_minutes": session_minutes,
        "has_chronic_conditions": bool(data["hasChronicConditions"]),
        "body_scan_consent": bool(data["bodyScanConsent"]),
        "body_scan_skipped": bool(data["bodyScanSkipped"]),
        "assessment_confirmed": True,
        "warnings": warnings,
        "equipment": equipment,
    }, []


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def api_v1_post_user_assessment(request):
    if request.method == "OPTIONS":
        return JsonResponse({})

    if not request.user.is_authenticated:
        return JsonResponse(
            {"detail": "Требуется авторизация", "code": "unauthorized"},
            status=401,
        )

    if request.method == "GET":
        assessment = (
            FitnessAssessment.objects.filter(user=request.user)
            .order_by("-assessment_completed_at")
            .first()
        )
        if assessment is None:
            return JsonResponse({"hasAssessment": False})
        return JsonResponse(
            {
                "hasAssessment": True,
                "assessmentCompletedAt": assessment.assessment_completed_at.isoformat(),
            }
        )

    return _create_assessment_response(request, user=request.user)


@require_http_methods(["POST", "OPTIONS"])
def api_v1_post_user_assessment_dev(request):
    if request.method == "OPTIONS":
        return JsonResponse({})
    if not settings.DEBUG:
        return JsonResponse({"detail": "Not found"}, status=404)
    return _create_assessment_response(request, user=None, dev=True)


def _create_assessment_response(request, user, dev: bool = False):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"fieldErrors": [_err("body", "invalid_json", "Некорректный JSON")]},
            status=400,
        )

    normalized, errors = validate_assessment_body(data)
    if errors:
        return JsonResponse({"fieldErrors": errors}, status=400)
    assert normalized is not None

    assessment = FitnessAssessment.objects.create(
        user=user,
        schema_version=int(data.get("schemaVersion", 1)),
        gender=normalized["gender"],
        age_years=normalized["age_years"],
        height_cm=normalized["height_cm"],
        weight_kg=normalized["weight_kg"],
        primary_goal=normalized["primary_goal"],
        fitness_level=normalized["fitness_level"],
        workouts_per_week=normalized["workouts_per_week"],
        preferred_session_minutes=normalized["preferred_session_minutes"],
        has_chronic_conditions=normalized["has_chronic_conditions"],
        body_scan_consent=normalized["body_scan_consent"],
        body_scan_skipped=normalized["body_scan_skipped"],
        assessment_confirmed=normalized["assessment_confirmed"],
        payload=data,
    )

    next_pid = None
    try:
        from main.views.assessment_plan_stub import stub_generate_training_plan

        stub_generate_training_plan(assessment, data)
        assessment.refresh_from_db()
        next_pid = assessment.next_recommended_program_id
    except Exception as e:
        logger.warning("assessment plan generation failed: %s", e)

    payload = {
        "assessmentCompletedAt": assessment.assessment_completed_at.isoformat(),
        "profileId": str(assessment.profile_id),
        "nextRecommendedProgramId": next_pid,
        "warnings": normalized.get("warnings") or [],
    }
    if dev:
        payload["dev"] = True
    return JsonResponse(payload, status=200)
