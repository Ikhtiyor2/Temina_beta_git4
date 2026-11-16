from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from main.models import (
    FitnessAssessment,
    WeeklyPlan,
    WeeklyPlanDay,
    WeeklyPlanDayExercise,
    WeeklyPlanSessionLog,
)
from main.services.weekly_plan_service import (
    monday_of,
    replace_weekly_plan_for_user,
    session_met_target,
    simple_session_feedback,
)
from main.views.api_v1_helpers import get_workout, json_error, parse_json_body, request_lang, require_authenticated_json


def _pick_lang(lang: str, ru: str, en: str, uz: str) -> str:
    key = (lang or "ru").lower()
    if key == "en":
        return en
    if key == "uz":
        return uz
    return ru


WORKOUT_TITLE_I18N = {
    "pushup_classic": ("Классические отжимания", "Classic push-ups", "Klassik otjimaniyalar"),
    "pullup_classic": ("Классические подтягивания", "Classic pull-ups", "Klassik tortilishlar"),
    "squat_classic": ("Классические приседания", "Classic squats", "Klassik o‘tirib-turishlar"),
    "crunch_classic": ("Классические скручивания", "Classic crunches", "Klassik bukilishlar"),
    "tabata_classic": ("Табата", "Tabata", "Tabata"),
    "run_classic": ("Бег", "Run", "Yugurish"),
}

DAY_TITLE_I18N = {
    "Силовой комплекс": ("Силовой комплекс", "Strength circuit", "Kuch kompleksi"),
    "Ноги и кор": ("Ноги и кор", "Legs and core", "Oyoqlar va kor"),
    "Верх и пресс": ("Верх и пресс", "Upper body and abs", "Yuqori tana va press"),
    "Функциональный день": ("Функциональный день", "Functional day", "Funksional kun"),
    "Смешанная тренировка": ("Смешанная тренировка", "Mixed workout", "Aralash mashg'ulot"),
    "Силовой день": ("Силовой день", "Strength day", "Kuch kuni"),
    "Полный комплекс": ("Полный комплекс", "Full-body circuit", "To'liq kompleks"),
    "Отдых": ("Отдых", "Rest", "Dam olish"),
}

FOCUS_NOTE_I18N = {
    "Восстановление и сон": ("Восстановление и сон", "Recovery and sleep", "Tiklanish va uyqu"),
}


def _localized_workout_title(counter_profile_id: str, fallback: str, lang: str) -> str:
    localized = WORKOUT_TITLE_I18N.get((counter_profile_id or "").lower())
    if localized:
        return _pick_lang(lang, *localized)
    return fallback


def _localized_day_title(raw_title: str, *, is_rest: bool, lang: str) -> str:
    if is_rest and not raw_title:
        raw_title = "Отдых"
    localized = DAY_TITLE_I18N.get(raw_title)
    if localized:
        return _pick_lang(lang, *localized)
    return raw_title


def _localized_focus_note(day: WeeklyPlanDay, exercises: list[dict], lang: str) -> str:
    if day.is_rest:
        raw = day.focus_note or "Восстановление и сон"
        localized = FOCUS_NOTE_I18N.get(raw)
        return _pick_lang(lang, *localized) if localized else raw
    if not exercises:
        return day.focus_note
    titles = [str(ex.get("title") or ex.get("counterProfileId") or "") for ex in exercises[:3] if ex.get("title") or ex.get("counterProfileId")]
    if not titles:
        return day.focus_note
    focus = " · ".join(titles)
    extra = len(exercises) - len(titles)
    if extra > 0:
        focus += _pick_lang(lang, f" и ещё {extra}", f" and {extra} more", f" va yana {extra} ta")
    return focus


def _serialize_exercise(ex: WeeklyPlanDayExercise, lang: str) -> dict:
    w = get_workout(ex.counter_profile_id)
    parent = (w.get("parentType") if w else "") or ""
    fallback = ex.display_title or (w.get("title") if w else "")
    return {
        "id": ex.id,
        "sortOrder": ex.sort_order,
        "counterProfileId": ex.counter_profile_id,
        "title": _localized_workout_title(ex.counter_profile_id, fallback, lang),
        "targetSets": ex.target_sets,
        "targetReps": ex.target_reps,
        "durationSec": ex.duration_sec,
        "completed": ex.completed,
        "parentType": parent,
    }


def _serialize_day(d: WeeklyPlanDay, lang: str) -> dict:
    exercises = [_serialize_exercise(ex, lang) for ex in d.exercises.all()]
    first = exercises[0] if exercises else None
    w = get_workout(d.counter_profile_id) if d.counter_profile_id and not first else None
    fallback_title = d.display_title or (first["title"] if first else (w.get("title") if w else ""))
    return {
        "id": d.id,
        "dayIndex": d.day_index,
        "isRest": d.is_rest,
        "title": _localized_day_title(fallback_title, is_rest=d.is_rest, lang=lang),
        "focusNote": _localized_focus_note(d, exercises, lang),
        "completed": d.completed,
        "exercises": exercises,
        "counterProfileId": first["counterProfileId"] if first else d.counter_profile_id,
        "targetSets": first["targetSets"] if first else d.target_sets,
        "targetReps": first["targetReps"] if first else d.target_reps,
        "durationSec": first["durationSec"] if first else d.duration_sec,
        "parentType": first["parentType"] if first else ((w.get("parentType") if w else "") or ""),
    }


def _serialize_plan(plan: WeeklyPlan, lang: str) -> dict:
    days = plan.days.prefetch_related("exercises").all()
    return {
        "id": plan.id,
        "weekStart": plan.week_start.isoformat(),
        "difficultyTier": plan.difficulty_tier,
        "source": plan.source,
        "days": [_serialize_day(d, lang) for d in days],
    }


@require_GET
def api_v1_week_plan_current(request):
    err = require_authenticated_json(request)
    if err:
        return err
    lang = request_lang(request)
    mon = monday_of()
    plan = (
        WeeklyPlan.objects.filter(user=request.user, week_start=mon)
        .prefetch_related("days__exercises")
        .first()
    )
    if plan is None:
        return JsonResponse(
            {
                "weekPlan": None,
                "detail": _pick_lang(
                    lang,
                    "План недели появится после анкеты или кнопки «Обновить».",
                    "Your week plan will appear after the assessment or after tapping Refresh.",
                    "Haftalik reja anketa to'ldirilgandan yoki Yangilash tugmasi bosilgandan keyin paydo bo'ladi.",
                ),
            }
        )
    return JsonResponse({"weekPlan": _serialize_plan(plan, lang)})


@csrf_exempt
@require_POST
def api_v1_week_plan_refresh(request):
    err = require_authenticated_json(request)
    if err:
        return err
    lang = request_lang(request)

    assessment = FitnessAssessment.objects.filter(user=request.user).order_by("-assessment_completed_at").first()
    if assessment is None:
        return json_error(
            _pick_lang(
                lang,
                "Сначала заполните анкету",
                "Complete the assessment first",
                "Avval anketani to'ldiring",
            ),
            status=400,
            code="no_assessment",
        )

    body, jerr = parse_json_body(request)
    if jerr:
        return jerr
    body = body or {}
    next_tier = request.user.weekly_plans.order_by("-week_start").first()
    tier = int(body.get("nextTier") or ((next_tier.difficulty_tier + 1) if next_tier else 1))
    tier = max(1, min(10, tier))

    plan = replace_weekly_plan_for_user(
        request.user,
        assessment,
        week_start=monday_of(),
        tier=tier,
        source=str(body.get("source") or "refresh"),
    )
    return JsonResponse({"weekPlan": _serialize_plan(plan, lang)})


@csrf_exempt
@require_POST
def api_v1_week_plan_log_session(request):
    err = require_authenticated_json(request)
    if err:
        return err
    lang = request_lang(request)
    body, jerr = parse_json_body(request)
    if jerr:
        return jerr
    body = body or {}

    day_id = body.get("weeklyPlanDayId")
    exercise_id = body.get("weeklyPlanDayExerciseId")
    try:
        day_id = int(day_id)
    except (TypeError, ValueError):
        return json_error("weeklyPlanDayId required", status=400, code="invalid_day")

    reps = int(body.get("reps") or 0)
    duration_sec = int(body.get("durationSec") or body.get("duration_seconds") or 0)
    quality = body.get("qualityScore")
    try:
        quality_f = float(quality) if quality is not None else None
    except (TypeError, ValueError):
        quality_f = None
    errors = body.get("errors") or []
    if not isinstance(errors, list):
        errors = []

    day = (
        WeeklyPlanDay.objects.select_related("plan")
        .prefetch_related("exercises")
        .filter(id=day_id, plan__user=request.user)
        .first()
    )
    if day is None:
        return json_error("День плана не найден", status=404, code="not_found")

    if day.is_rest:
        return json_error("Этот день — отдых", status=400, code="rest_day")

    exercise: WeeklyPlanDayExercise | None = None
    if exercise_id is not None:
        try:
            exercise_id = int(exercise_id)
        except (TypeError, ValueError):
            return json_error("weeklyPlanDayExerciseId invalid", status=400, code="invalid_exercise")
        exercise = day.exercises.filter(id=exercise_id).first()
        if exercise is None:
            return json_error("Упражнение не найдено в этом дне", status=404, code="exercise_not_found")
    else:
        profile = body.get("counterProfileId") or ""
        if profile:
            exercise = day.exercises.filter(counter_profile_id=profile).first()
        if exercise is None and day.exercises.count() == 1:
            exercise = day.exercises.first()

    if exercise is None:
        return json_error(
            "weeklyPlanDayExerciseId required",
            status=400,
            code="exercise_required",
        )

    profile = body.get("counterProfileId") or exercise.counter_profile_id
    if profile and profile != exercise.counter_profile_id:
        return json_error("counterProfileId не совпадает с планом", status=400, code="profile_mismatch")

    w = get_workout(exercise.counter_profile_id)
    parent = (w.get("parentType") if w else "") or ""

    met = session_met_target(
        parent_type=parent,
        target_reps=exercise.target_reps,
        target_sets=exercise.target_sets,
        duration_target=exercise.duration_sec,
        reps=reps,
        duration_sec=duration_sec,
    )

    feedback = simple_session_feedback(
        target_reps=exercise.target_reps,
        target_sets=exercise.target_sets,
        duration_target=exercise.duration_sec,
        reps=reps,
        duration_sec=duration_sec,
        errors=errors,
        met_target=met,
    )

    log = WeeklyPlanSessionLog.objects.create(
        plan=day.plan,
        day=day,
        exercise=exercise,
        counter_profile_id=exercise.counter_profile_id,
        reps=reps,
        duration_sec=duration_sec,
        quality_score=quality_f,
        errors_json=errors,
        ai_feedback=feedback,
    )

    if met:
        exercise.completed = True
        exercise.save(update_fields=["completed"])
    day.refresh_completed_from_exercises()

    plan = WeeklyPlan.objects.prefetch_related("days__exercises").get(pk=day.plan_id)

    return JsonResponse(
        {
            "ok": True,
            "metTarget": met,
            "exerciseCompleted": exercise.completed,
            "dayCompleted": day.completed,
            "logId": log.id,
            "aiFeedback": feedback,
            "weekPlan": _serialize_plan(plan, lang),
        }
    )


@csrf_exempt
@require_POST
def api_v1_week_plan_rollover(request):
    err = require_authenticated_json(request)
    if err:
        return err
    lang = request_lang(request)

    assessment = FitnessAssessment.objects.filter(user=request.user).order_by("-assessment_completed_at").first()
    if assessment is None:
        return json_error("Нет анкеты", status=400, code="no_assessment")

    next_mon = monday_of() + timedelta(days=7)
    prev = WeeklyPlan.objects.filter(user=request.user).order_by("-week_start").first()
    tier = (prev.difficulty_tier + 1) if prev else 1
    tier = max(1, min(10, tier))

    plan = replace_weekly_plan_for_user(
        request.user,
        assessment,
        week_start=next_mon,
        tier=tier,
        source="rollover",
    )
    return JsonResponse({"weekPlan": _serialize_plan(plan, lang)})
