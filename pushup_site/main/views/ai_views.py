# main/views/ai_views.py
import json
import base64
import logging
import time
import traceback

import cv2
import numpy as np

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.middleware.csrf import get_token
from django.conf import settings

from main.pose_manager import PoseManager
from main.exercises import (
    PushupWorkout,
    SquatWorkout,
    PullupWorkout,
    CrunchesWorkout,
    PlankWorkout,
)
from main.models import Player, ActiveWorkout

logger = logging.getLogger(__name__)

MAX_AI_FRAME_BYTES = 2 * 1024 * 1024

# ======================================================
# DETECTOR FACTORY
# ======================================================

DETECTOR_MAP = {
    "PUSHUP": PushupWorkout,
    "SQUAT": SquatWorkout,
    "PULLUP": PullupWorkout,
    "CRUNCH": CrunchesWorkout,
    "PLANK": PlankWorkout,
}


def normalize_exercise_type(exercise_type: str) -> str:
    ex = (exercise_type or "PUSHUP").strip().upper()

    # Дополнительные варианты, если где-то придут другие имена
    if ex in ("PUSHUPS", "PUSH_UP"):
        return "PUSHUP"
    if ex in ("SQUATS",):
        return "SQUAT"
    if ex in ("CRUNCHES", "SITUP", "SITUPS"):
        return "CRUNCH"
    if ex in ("PLANKS",):
        return "PLANK"

    return ex


def get_detector(exercise_type: str):
    """Фабрика детекторов упражнений"""
    exercise_type = normalize_exercise_type(exercise_type)
    detector_cls = DETECTOR_MAP.get(exercise_type, PushupWorkout)
    return detector_cls()


def get_player_and_workout(user, exercise_type: str):
    """
    Единая функция получения Player + ActiveWorkout
    (чтобы не было расхождений между landmarks/frame API)
    """
    exercise_type = normalize_exercise_type(exercise_type)

    player, _ = Player.objects.get_or_create(user=user)

    workout, _created = ActiveWorkout.get_or_create_active(
        player=player,
        exercise_type=exercise_type
    )
    return player, workout


# ======================================================
# CORE AI ENDPOINT (FRAME → SERVER → MEDIAPIPE)
# ======================================================

@login_required
@require_POST
def process_ai_frame(request):
    """
    Принимает JPEG кадр с камеры браузера,
    обрабатывает через MediaPipe Pose,
    считает упражнение,
    возвращает JSON для HUD + skeleton.
    """
    start_time = time.time()

    logger.info(f"🎯 AI frame request from user: {request.user.username}")

    if not request.body:
        logger.error("❌ Empty request body")
        return JsonResponse(
            {"success": False, "error": "empty_body", "message": "Request body is empty"},
            status=400,
        )

    if len(request.body) > MAX_AI_FRAME_BYTES:
        return JsonResponse(
            {"success": False, "error": "payload_too_large", "message": "Frame payload too large"},
            status=413,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error: {e}")
        return JsonResponse(
            {"success": False, "error": "invalid_json", "message": "Invalid JSON format"},
            status=400,
        )

    frame_data = data.get("frame")
    exercise_type = normalize_exercise_type(data.get("exercise_type", "PUSHUP"))
    user_agent = request.headers.get("User-Agent", "")

    logger.info(f"🏋️ Exercise type: {exercise_type}")

    if not frame_data:
        logger.error("❌ Frame data missing")
        return JsonResponse(
            {"success": False, "error": "frame_missing", "message": "Frame data is required"},
            status=400,
        )

    # ==================================================
    # base64 → OpenCV
    # ==================================================
    try:
        if "," in frame_data:
            encoded = frame_data.split(",")[1]
        else:
            encoded = frame_data

        frame_bytes = base64.b64decode(encoded)
        frame_np = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(frame_np, cv2.IMREAD_COLOR)

        if frame is None:
            logger.error("❌ Failed to decode image from base64")
            return JsonResponse(
                {"success": False, "error": "decode_failed", "message": "Failed to decode image"},
                status=400,
            )

    except Exception as e:
        logger.error(f"❌ Error decoding frame: {e}")
        return JsonResponse(
            {"success": False, "error": "frame_decode_error", "message": str(e)},
            status=400,
        )

    # ==================================================
    # АКТИВНАЯ ТРЕНИРОВКА
    # ==================================================
    try:
        player, workout = get_player_and_workout(request.user, exercise_type)
    except Exception as e:
        logger.error(f"❌ Error getting ActiveWorkout: {e}")
        return JsonResponse(
            {"success": False, "error": "workout_error", "message": str(e)},
            status=500,
        )

    # ==================================================
    # ОБРАБОТКА ПОЗЫ
    # ==================================================
    try:
        detector = get_detector(exercise_type)
        state = {
            "count": workout.count,
            "stage": workout.stage,
            "ready": workout.ready,
        }
        if exercise_type == "SQUAT" and workout.frame_data:
            state["min_knee_angle_in_rep"] = workout.frame_data.get("min_knee_angle_in_rep", 180)
        if exercise_type == "PLANK" and workout.frame_data:
            state["max_hold_seconds"] = workout.frame_data.get("max_hold_seconds", 0)
            state["current_hold_seconds"] = workout.frame_data.get("current_hold_seconds", 0)
        detector.load_state(state)

        user_agent_lower = user_agent.lower()
        if any(mobile in user_agent_lower for mobile in ["mobile", "android", "iphone"]):
            device_type = "mobile"
        else:
            device_type = "desktop"

        processing_time_pose = 0
        results = None

        try:
            with PoseManager(device_type=device_type) as pose_manager:
                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                pose_start = time.time()
                results = pose_manager.process(image_rgb, calculate_metrics=True)
                processing_time_pose = time.time() - pose_start

        except Exception as e:
            logger.error(f"❌ PoseManager error: {e}", exc_info=True)

        pose_detected = False
        feedback = "Инициализация..."
        errors = []
        landmarks = []
        pose_quality = "unknown"

        if results and results.pose_landmarks:
            pose_detected = True

            # качество позы
            try:
                avg_visibility = sum(
                    [lm.visibility for lm in results.pose_landmarks.landmark]
                ) / len(results.pose_landmarks.landmark)

                if avg_visibility > 0.7:
                    pose_quality = "good"
                elif avg_visibility > 0.4:
                    pose_quality = "needs_improvement"
                else:
                    pose_quality = "poor"
            except Exception:
                pose_quality = "unknown"

            # упражнение
            try:
                feedback, errors = detector._process_pose(results.pose_landmarks)
                # Нормализуем: каждый элемент — dict с message и hint; сортируем по priority (1 = важнее)
                errors = [
                    e if isinstance(e, dict) and "message" in e and "hint" in e
                    else {"message": str(e), "hint": "Поправьте позу и повторите."}
                    for e in (errors or [])
                ]
                errors.sort(key=lambda e: e.get("priority", 99))
                errors = errors[:4]
            except Exception as e:
                logger.error(f"❌ Error processing pose: {e}", exc_info=True)
                feedback = "Ошибка обработки позы"
                errors = [{"message": f"Ошибка: {str(e)}", "hint": "Убедитесь, что в кадре всё тело, или перезагрузите страницу."}]

            # landmarks для skeleton (ключевые точки)
            key_landmarks = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
            for i in key_landmarks:
                if i < len(results.pose_landmarks.landmark):
                    lm = results.pose_landmarks.landmark[i]
                    landmarks.append({
                        "x": float(lm.x),
                        "y": float(lm.y),
                        "z": float(lm.z),
                        "visibility": float(lm.visibility),
                        "id": i
                    })

        else:
            feedback = "Поза не обнаружена. Убедитесь, что вы в поле зрения камеры."
            pose_quality = "no_pose"

        # ==================================================
        # СОХРАНЯЕМ СОСТОЯНИЕ В БД
        # ==================================================
        total_processing_time = time.time() - start_time

        fd = {
            "count": detector.count,
            "stage": detector.stage,
            "ready": detector.ready,
            "feedback": feedback,
            "errors": errors,
            "pose_detected": pose_detected,
            "pose_quality": pose_quality,
            "landmarks_count": len(landmarks),
            "processing_time_ms": total_processing_time * 1000,
            "pose_processing_time_ms": processing_time_pose * 1000,
            "timestamp": timezone.now().isoformat(),
        }
        if exercise_type == "SQUAT":
            fd["min_knee_angle_in_rep"] = getattr(detector, "min_knee_angle_in_rep", 180)
        if exercise_type == "PLANK":
            fd["max_hold_seconds"] = getattr(detector, "max_hold_seconds", 0)
            fd["current_hold_seconds"] = getattr(detector, "current_hold_seconds", 0)

        with transaction.atomic():
            locked = ActiveWorkout.objects.select_for_update().get(pk=workout.pk)
            locked.count = detector.count
            locked.stage = detector.stage
            locked.ready = detector.ready
            locked.last_update = timezone.now()
            try:
                locked.update_frame_data(fd)
            except Exception as e:
                logger.warning(f"⚠️ Error updating frame data: {e}")
            locked.save()
            workout = locked

        response_data = {
            "success": True,
            "exercise": exercise_type,

            "debug": {
                "pose_manager_working": bool(results),
                "landmarks_found": len(landmarks) if landmarks else 0,
                "detector_type": detector.__class__.__name__,
                "image_size": f"{frame.shape[1]}x{frame.shape[0]}",
                "frame_data_length": len(frame_data) if frame_data else 0,
            },

            "pose_detected": pose_detected,
            "pose_quality": pose_quality,
            "landmarks": landmarks,

            "count": int(detector.count),
            "stage": str(detector.stage),
            "ready": bool(detector.ready),
            "feedback": str(feedback),
            "errors": list(errors),

            "processing_time_ms": round(total_processing_time * 1000, 1),
            "pose_processing_time_ms": round(processing_time_pose * 1000, 1),

            "workout_id": int(workout.id),
            "session_id": str(request.session.session_key) if request.session.session_key else "no-session",

            "csrf_token": get_token(request),
            "server_time": timezone.now().isoformat(),
        }

        logger.info(
            f"✅ AI Frame processed: user={request.user.username}, "
            f"exercise={exercise_type}, count={detector.count}, "
            f"pose_detected={pose_detected}, time={total_processing_time*1000:.1f}ms"
        )

        return JsonResponse(response_data)

    except Exception as e:
        logger.exception(f"❌ CRITICAL ERROR in AI processing: {e}")

        error_data = {
            "success": False,
            "error": "processing_error",
            "message": str(e),
            "processing_time_ms": round((time.time() - start_time) * 1000, 1)
        }

        if settings.DEBUG:
            error_data["traceback"] = traceback.format_exc()

        return JsonResponse(error_data, status=500)


# ======================================================
# LANDMARKS ENDPOINT (BROWSER → SERVER)
# ======================================================

@login_required
@require_POST
def process_landmarks(request):
    """
    Принимает landmarks от mediapipe из браузера.

    ВАЖНО:
    - НЕ создаём detector заново без состояния
    - Загружаем count/stage/ready из ActiveWorkout
    - После обработки сохраняем обратно
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"success": False, "error": "invalid_json"}, status=400)

    exercise_type = normalize_exercise_type(data.get("exercise_type", "PUSHUP"))
    landmarks = data.get("landmarks")

    if not isinstance(landmarks, list) or len(landmarks) < 10:
        return JsonResponse({"success": False, "error": "invalid_landmarks"}, status=400)

    try:
        player, workout = get_player_and_workout(request.user, exercise_type)
    except Exception as e:
        return JsonResponse({"success": False, "error": "workout_error", "message": str(e)}, status=500)

    # берём детектор
    detector = get_detector(exercise_type)

    state = {
        "count": workout.count,
        "stage": workout.stage,
        "ready": workout.ready,
    }
    if exercise_type == "SQUAT" and workout.frame_data:
        state["min_knee_angle_in_rep"] = workout.frame_data.get("min_knee_angle_in_rep", 180)
    if exercise_type == "PLANK" and workout.frame_data:
        state["max_hold_seconds"] = workout.frame_data.get("max_hold_seconds", 0)
        state["current_hold_seconds"] = workout.frame_data.get("current_hold_seconds", 0)
    detector.load_state(state)

    # ==================================================
    # ОБРАБОТКА LANDMARKS (адаптер под _process_pose)
    # ==================================================
    try:
        # Браузер присылает массив точек; _process_pose ждёт объект с .landmark
        class LandmarkObj:
            __slots__ = ("x", "y", "z", "visibility")
            def __init__(self, x=0, y=0, z=0, visibility=1):
                self.x = float(x)
                self.y = float(y)
                self.z = float(z)
                self.visibility = float(visibility)

        landmark_list = []
        for pt in landmarks:
            if isinstance(pt, dict):
                landmark_list.append(LandmarkObj(
                    pt.get("x", 0), pt.get("y", 0), pt.get("z", 0), pt.get("visibility", 1)
                ))
            else:
                landmark_list.append(LandmarkObj(
                    getattr(pt, "x", 0), getattr(pt, "y", 0), getattr(pt, "z", 0), getattr(pt, "visibility", 1)
                ))
        while len(landmark_list) < 33:
            landmark_list.append(LandmarkObj(0, 0, 0, 0))

        class PoseLandmarks:
            pass
        pl = PoseLandmarks()
        pl.landmark = landmark_list
        feedback, errors = detector._process_pose(pl)
        errors = [
            e if isinstance(e, dict) and "message" in e and "hint" in e
            else {"message": str(e), "hint": "Поправьте позу и повторите."}
            for e in (errors or [])
        ]
        errors.sort(key=lambda e: e.get("priority", 99))
        errors = errors[:4]
    except Exception as e:
        logger.error(f"❌ process_landmarks detector error: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": "detector_error", "message": str(e)}, status=500)

    # ==================================================
    # СОХРАНЯЕМ СОСТОЯНИЕ
    # ==================================================
    try:
        workout.count = int(detector.count)
        workout.stage = str(detector.stage)
        workout.ready = bool(getattr(detector, "ready", workout.ready))
        workout.last_update = timezone.now()
        if exercise_type == "SQUAT":
            workout.frame_data = dict(workout.frame_data or {})
            workout.frame_data["min_knee_angle_in_rep"] = getattr(detector, "min_knee_angle_in_rep", 180)
        if exercise_type == "PLANK":
            workout.frame_data = dict(workout.frame_data or {})
            workout.frame_data["max_hold_seconds"] = getattr(detector, "max_hold_seconds", 0)
            workout.frame_data["current_hold_seconds"] = getattr(detector, "current_hold_seconds", 0)
        workout.save()
    except Exception as e:
        logger.error(f"❌ Error saving workout state: {e}", exc_info=True)

    return JsonResponse({
        "success": True,
        "exercise": exercise_type,
        "count": int(workout.count),
        "stage": str(workout.stage),
        "ready": bool(workout.ready),
        "feedback": str(feedback),
        "errors": list(errors),
    })


# ======================================================
# GET AI STATE
# ======================================================

@login_required
@require_GET
def get_ai_state(request):
    """Текущее состояние упражнения (для polling HUD)"""
    exercise_type = normalize_exercise_type(request.GET.get("exercise", "PUSHUP"))

    try:
        player = Player.objects.get(user=request.user)
        workout = ActiveWorkout.objects.get(
            player=player,
            exercise_type=exercise_type,
            is_active=True
        )

        return JsonResponse({
            "success": True,
            "exercise": exercise_type,
            "count": workout.count,
            "stage": workout.stage,
            "ready": workout.ready,
            "is_active": workout.is_active,
            "duration_seconds": workout.get_duration_seconds(),
            "workout_id": workout.id,
            "last_update": workout.last_update.isoformat() if workout.last_update else None,
        })

    except ActiveWorkout.DoesNotExist:
        return JsonResponse({
            "success": True,
            "exercise": exercise_type,
            "count": 0,
            "stage": "up",
            "ready": False,
            "is_active": False,
            "duration_seconds": 0,
            "workout_id": None,
            "last_update": None,
        })
    except Exception as e:
        logger.error(f"Error getting AI state: {e}")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# GET CSRF TOKEN
# ======================================================

@ensure_csrf_cookie
@require_GET
def get_csrf_token(request):
    """Возвращает CSRF токен для использования в заголовках (в т.ч. до login/register)."""
    token = get_token(request)
    user_label = request.user.username if request.user.is_authenticated else "anonymous"
    logger.info(f"🔑 CSRF token requested by {user_label}: {token[:10]}...")
    return JsonResponse({
        "success": True,
        "csrf_token": token,
        "session_id": request.session.session_key,
    })


# ======================================================
# RESET AI STATE
# ======================================================

@login_required
@require_POST
def reset_ai_state(request):
    """Сброс состояния упражнения"""
    try:
        data = json.loads(request.body)
        exercise_type = normalize_exercise_type(data.get("exercise_type", "PUSHUP"))

        player = Player.objects.get(user=request.user)
        workout = ActiveWorkout.objects.get(
            player=player,
            exercise_type=exercise_type
        )

        old_count = workout.count
        workout.reset()

        logger.info(
            f"Reset AI state: user={request.user.username}, "
            f"exercise={exercise_type}, old_count={old_count}"
        )

        return JsonResponse({
            "success": True,
            "message": "AI state reset",
            "exercise": exercise_type,
            "old_count": old_count,
        })

    except ActiveWorkout.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "no_active_workout",
            "message": "No active workout found"
        }, status=404)

    except Exception as e:
        logger.exception("Error resetting AI state")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# EXPORTS
# ======================================================

__all__ = [
    "process_ai_frame",
    "process_landmarks",
    "get_ai_state",
    "get_csrf_token",
    "reset_ai_state",
]
