# main/views/workout_views.py
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from main.models import WorkoutSession, WorkoutSet, Player, ActiveWorkout
from main.quest_manager import QuestManager
from main.views.api_v1_helpers import active_workout_duration_seconds, clamp_workout_duration_seconds
from main.integrity import sanitize_client_reps
from main.workout_completion import apply_skill_bonuses, finalize_workout, normalize_exercise_type

logger = logging.getLogger(__name__)

ALLOWED_EXERCISE_TYPES = {
    "PUSHUP", "SQUAT", "PULLUP", "CRUNCH", "TABATA", "RUN",
}

STRENGTH_EXERCISES = {"PUSHUP", "PULLUP"}


def _apply_skill_bonuses(player, exercise_type, reps, base_calories):
    return apply_skill_bonuses(player, exercise_type, reps, base_calories)


# ======================================================
# START WORKOUT
# ======================================================

@login_required
@require_POST
def start_workout(request):
    """
    Инициализация тренировки.
    Создаёт или сбрасывает ActiveWorkout.
    """

    try:
        data = json.loads(request.body or "{}")
        exercise_type = data.get("exercise_type", "PUSHUP").upper()

        player, _ = Player.objects.get_or_create(user=request.user)

        if exercise_type == "TABATA":
            return JsonResponse({
                "success": True,
                "exercise": exercise_type,
                "message": "Tabata session started",
                "workout_id": None,
            })

        # если уже есть активная — сбрасываем
        workout, created = ActiveWorkout.objects.get_or_create(
            player=player,
            exercise_type=exercise_type,
            defaults={
                "count": 0,
                "stage": "up",
                "ready": False,
                "is_active": True,
                "start_time": timezone.now(),
                "last_update": timezone.now(),
            },
        )

        if not created:
            workout.is_active = True
            workout.count = 0
            workout.stage = "up"
            workout.ready = False
            workout.last_update = timezone.now()
            workout.save()

        return JsonResponse({
            "success": True,
            "exercise": exercise_type,
            "message": "Workout started",
            "workout_id": workout.id,
        })

    except Exception as e:
        logger.exception("Error starting workout")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# COMPLETE WORKOUT
# ======================================================

@login_required
@require_POST
def complete_workout(request):
    """
    Завершение тренировки.
    Берёт реальные данные из ActiveWorkout (а не session),
    сохраняет WorkoutSession, закрывает ActiveWorkout.
    """

    try:
        data = json.loads(request.body or "{}")
        exercise_type = data.get("exercise_type", "PUSHUP").upper()

        player, _ = Player.objects.get_or_create(user=request.user)

        # берём активную тренировку (может не быть, если камера не запускалась)
        workout = ActiveWorkout.objects.filter(
            player=player,
            exercise_type=exercise_type,
            is_active=True,
        ).first()

        # Клиент может прислать итоговое число повторений (всё считается на устройстве)
        reps = data.get("reps")
        if reps is not None:
            reps = int(reps)
        elif workout:
            reps = int(workout.count or 0)
        else:
            reps = 0

        integrity = data.get("integrity") or {}
        errors_count = 0
        if isinstance(integrity, dict):
            errors_count = int(integrity.get("critical_violations") or 0)

        server_count = int(workout.count or 0) if workout else None
        reps = sanitize_client_reps(
            reps,
            server_count=server_count,
            integrity=integrity if isinstance(integrity, dict) else None,
        )

        # длительность
        duration_sec_client = data.get("duration_sec")
        if duration_sec_client is not None:
            duration = clamp_workout_duration_seconds(duration_sec_client)
        elif workout:
            duration = active_workout_duration_seconds(workout)
        else:
            duration = 0

        intensity_score = float(data.get("intensity_score") or 0.0)
        tabata_program_id = data.get("tabata_program_id") or ""

        # калории с учётом бонусов от навыков; XP за занятия не начисляется
        if exercise_type == "TABATA":
            client_cal = data.get("calories")
            if client_cal is not None:
                base_calories = float(client_cal)
            else:
                # MET fallback: ~10 + intensity*4
                met = 10.0 + min(max(intensity_score, 0.35), 1.0) * 4.0
                weight_kg = 70.0
                try:
                    assessment = getattr(player, "assessment", None)
                    if assessment and getattr(assessment, "weight_kg", None):
                        weight_kg = float(assessment.weight_kg)
                except Exception:
                    pass
                active = max(duration * 0.55, float(reps) * 0.8)
                base_calories = met * weight_kg * (active / 3600.0) + float(reps) * 0.12
        else:
            base_calories = float(reps) * 0.5
        result = finalize_workout(
            player,
            exercise_type=exercise_type,
            reps=reps,
            duration_sec=max(0, duration),
            calories=base_calories,
            errors_count=errors_count,
            integrity=integrity if isinstance(integrity, dict) else None,
            server_count=server_count,
            intensity_score=intensity_score,
            user=request.user,
            update_quests=False,
        )
        # закрываем ActiveWorkout, если была активная
        if workout:
            workout.is_active = False
            workout.last_update = timezone.now()
            workout.save()

        # Обновляем прогресс квестов (ИИ-счётчик засчитывает повторения/секунды)
        try:
            quest_count = reps
            if exercise_type == "TABATA":
                quest_count = 1
            elif exercise_type == "RUN":
                quest_count = int(float((integrity or {}).get("distance_km") or 0) * 1000)
            QuestManager(player).update_quest_progress(exercise_type, quest_count)
        except Exception:
            logger.exception("Quest progress update failed")

        return JsonResponse({
            "success": True,
            "exercise": exercise_type,
            "reps": reps,
            "duration": duration,
            "calories": result["calories"],
            "xp_earned": result["xp_earned"],
            "xp_gained": result["xp_earned"],
            "baseXp": result.get("baseXp", result["xp_earned"]),
            "skillBonus": result.get("skillBonus", 0),
            "totalXp": result.get("totalXp", result["xp_earned"]),
            "leveled_up": result["leveled_up"],
            "session_id": result["session_id"],
        })

    except Exception as e:
        logger.exception("Error completing workout")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# SAVE SET (для страниц упражнений: скручивания, отжимания и т.д.)
# ======================================================

@login_required
@require_POST
def save_workout_set(request, exercise_type):
    """
    Сохраняет подход с страницы упражнения (crunches.html, pushups.html и т.д.).
    Принимает JSON с reps (опционально). Создаёт WorkoutSession и WorkoutSet.
    """
    try:
        exercise_type = (exercise_type or "PUSHUP").upper().replace(" ", "_")
        if exercise_type == "PULL_UPS":
            exercise_type = "PULLUP"
        if exercise_type not in ALLOWED_EXERCISE_TYPES:
            return JsonResponse(
                {"success": False, "error": "invalid_exercise_type"},
                status=400,
            )
        data = json.loads(request.body or "{}")
        reps = data.get("reps")
        if reps is not None:
            reps = int(reps)
        else:
            reps = 0

        player, _ = Player.objects.get_or_create(user=request.user)
        base_calories = float(reps) * 0.5
        result = finalize_workout(
            player,
            exercise_type=exercise_type,
            reps=reps,
            duration_sec=0,
            calories=base_calories,
            user=request.user,
        )
        return JsonResponse({
            "success": True,
            "exercise": exercise_type,
            "reps": reps,
            "calories": result["calories"],
            "xp_earned": result["xp_earned"],
            "xp_gained": result["xp_earned"],
            "leveled_up": result["leveled_up"],
            "session_id": result["session_id"],
        })
    except Exception as e:
        logger.exception("Error saving workout set")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# CURRENT WORKOUT STATUS
# ======================================================

@login_required
@require_GET
def get_current_workout(request, exercise_type):
    """
    Возвращает текущий статус активной тренировки.
    """

    try:
        exercise_type = (exercise_type or "PUSHUP").upper()

        player, _ = Player.objects.get_or_create(user=request.user)

        workout = ActiveWorkout.objects.filter(
            player=player,
            exercise_type=exercise_type,
            is_active=True,
        ).first()

        if not workout:
            return JsonResponse({
                "active": False,
                "exercise": exercise_type,
            })

        if workout.start_time:
            duration = int((timezone.now() - workout.start_time).total_seconds())
        else:
            duration = 0

        return JsonResponse({
            "active": True,
            "exercise": exercise_type,
            "count": int(workout.count or 0),
            "stage": str(workout.stage or "up"),
            "ready": bool(workout.ready),
            "duration": duration,
            "workout_id": workout.id,
        })

    except Exception as e:
        logger.exception("Error get_current_workout")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# RESET WORKOUT
# ======================================================

@login_required
@require_POST
def reset_workout(request):
    """
    Полный сброс тренировки без сохранения.
    Сбрасывает ActiveWorkout.
    """

    try:
        data = json.loads(request.body or "{}")
        exercise_type = data.get("exercise_type", "PUSHUP").upper()

        player, _ = Player.objects.get_or_create(user=request.user)

        workout = ActiveWorkout.objects.filter(
            player=player,
            exercise_type=exercise_type,
            is_active=True,
        ).first()

        if workout:
            workout.count = 0
            workout.stage = "up"
            workout.ready = False
            workout.last_update = timezone.now()
            workout.save()

        return JsonResponse({
            "success": True,
            "exercise": exercise_type,
            "message": "Workout reset",
        })

    except Exception as e:
        logger.exception("Error reset_workout")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )
