import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from ..models import Quest, Player
from ..quest_manager import QuestManager

logger = logging.getLogger(__name__)


# ======================================================
# HELPERS
# ======================================================

def _get_request_data(request):
    """
    Поддержка:
    - JSON body
    - обычный form-data POST
    """
    if request.method != "POST":
        return {}

    # 1) form-data
    if request.POST:
        return request.POST

    # 2) JSON
    try:
        body = request.body.decode("utf-8").strip()
        if body:
            return json.loads(body)
    except Exception:
        return {}

    return {}


def _player_for_request(request):
    """
    В проекте Player связан с User.
    Гарантируем, что Player существует.
    """
    player, _ = Player.objects.get_or_create(user=request.user)
    return player


def _serialize_player(player: Player):
    return {
        "level": int(getattr(player, "level", 1) or 1),
        "exp": float(getattr(player, "exp", 0) or 0),
        "exp_to_level": int(getattr(player, "exp_to_level", 100) or 100),
        "currency": int(getattr(player, "currency", 0) or 0),
        "skill_points": int(getattr(player, "skill_points", 0) or 0),
    }


def _safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


def _quest_percent(progress, goal):
    goal = max(1, _safe_int(goal, 1))
    progress = max(0, _safe_int(progress, 0))
    return max(0, min(100, int(round((progress / goal) * 100))))


def _serialize_quest_for_api(q: Quest):
    """
    Унифицированный формат для фронта.
    """

    progress = _safe_int(getattr(q, "progress", 0), 0)
    goal = _safe_int(getattr(q, "goal", 1), 1)

    completed = bool(getattr(q, "completed", False))
    active = bool(getattr(q, "active", True))  # если поля active нет — считаем активным
    percent = _quest_percent(progress, goal)

    # ready = достиг цели, но ещё не completed
    ready = (not completed) and (progress >= goal)

    # exercise_type / quest_type для связи с ИИ-счётчиком
    exercise_type = getattr(q, "quest_type", "") or getattr(q, "exercise_type", "") or getattr(q, "exercise", "") or ""

    # Ссылка на страницу тренировки с ИИ-счётчиком по типу квеста
    TRAINING_URLS = {
        "PUSHUP": "/train/pushups/",
        "SQUAT": "/train/squats/",
        "CRUNCH": "/train/crunches/",
        "PLANK": "/train/planks/",
        "PULLUP": "/train/pullups/",
    }
    training_url = TRAINING_URLS.get((exercise_type or "").upper(), "") if exercise_type else ""

    # награды
    reward_xp = _safe_int(getattr(q, "reward_xp", 0), 0)
    reward_currency = _safe_int(getattr(q, "reward_currency", 0), 0)
    reward_skill_points = _safe_int(getattr(q, "reward_skill_points", 0), 0)

    # красивые поля для UI
    title = getattr(q, "title", None) or "Квест"
    description = getattr(q, "description", None) or "Выполните задание, чтобы получить награду."

    # Иконка (если в модели нет — дефолт)
    icon = getattr(q, "icon", None) or "ri-flag-2-line"

    # difficulty (если в модели нет — обычный)
    difficulty = getattr(q, "difficulty", None) or "Обычный"

    # подсказка что делать
    action_text = getattr(q, "action_text", None)
    if not action_text:
        if exercise_type:
            action_text = f"Сделайте {goal} повторений ({exercise_type})"
        else:
            action_text = f"Достигните цели: {goal}"

    return {
        "id": q.id,
        "title": title,
        "description": description,
        "action_text": action_text,

        "exercise_type": exercise_type,
        "quest_type": exercise_type,
        "training_url": training_url,

        "progress": progress,
        "goal": goal,

        # совместимость
        "progress_percent": percent,
        "progress_percentage": percent,

        "is_active": active and (not completed),
        "is_completed": completed,
        "is_ready": ready,

        "difficulty": difficulty,
        "icon": icon,

        "reward": reward_xp,
        "reward_xp": reward_xp,
        "reward_currency": reward_currency,
        "reward_skill_points": reward_skill_points,
    }


def _ensure_quests_exist(player: Player):
    """
    Если квестов нет — создаём стартовые.
    Если есть — генерируем ежедневные (как у тебя было).
    """
    quest_manager = QuestManager(player)

    try:
        if Quest.objects.filter(player=player).count() == 0:
            quest_manager.create_initial_quests()
        else:
            quest_manager.generate_daily_quests()
    except Exception:
        # Даже если генератор упадёт — не ломаем API
        logger.exception("Quest generation failed")

    return quest_manager


# ======================================================
# GET QUESTS (FULL)
# ======================================================

@login_required
@require_GET
def get_quests(request):
    """
    Полный список квестов для страницы.
    """
    try:
        player = _player_for_request(request)
        quest_manager = _ensure_quests_exist(player)

        quests_qs = Quest.objects.filter(player=player).order_by("-id")
        quests = [_serialize_quest_for_api(q) for q in quests_qs]

        return JsonResponse({
            "success": True,
            "quests": quests,
            "player": _serialize_player(player),
            "server_time": timezone.now().isoformat(),
        })

    except Exception as e:
        logger.exception("Error loading quests")
        return JsonResponse(
            {"success": False, "error": str(e), "quests": []},
            status=500,
        )


# ======================================================
# QUESTS DATA (AUTO UPDATE)
# ======================================================

@login_required
@require_GET
def quests_data(request):
    """
    ЭТО ТО, ЧТО ТЫ ДЁРГАЕШЬ ИЗ quests.html
    /api/quests-data/

    Раньше ты отдавал только compact.
    Сейчас отдаём ПОЛНЫЙ формат, чтобы UI был нормальным.
    """
    try:
        player = _player_for_request(request)
        _ensure_quests_exist(player)

        quests_qs = Quest.objects.filter(player=player).order_by("-id")
        quests = [_serialize_quest_for_api(q) for q in quests_qs]

        return JsonResponse({
            "success": True,
            "quests": quests,
            "server_time": timezone.now().isoformat(),
        })

    except Exception as e:
        logger.exception("Error loading quests data")
        return JsonResponse(
            {"success": False, "error": str(e), "quests": []},
            status=500,
        )


# ======================================================
# START QUEST
# ======================================================

@login_required
@require_POST
def start_quest(request):
    """
    Начать квест.
    ВАЖНО:
    - у тебя раньше просто progress=0 и всё
    - но фронт ждет is_active=True
    """
    try:
        data = _get_request_data(request)
        quest_id = data.get("quest_id")

        if not quest_id:
            return JsonResponse({"success": False, "error": "quest_id_required"}, status=400)

        player = _player_for_request(request)

        quest = Quest.objects.get(id=quest_id, player=player)

        # Сброс
        quest.completed = False
        quest.progress = 0

        # Если есть поле active — включаем
        if hasattr(quest, "active"):
            quest.active = True

        quest.save()

        return JsonResponse({
            "success": True,
            "message": "Quest started",
            "quest": _serialize_quest_for_api(quest),
            "player": _serialize_player(player),
        })

    except Quest.DoesNotExist:
        return JsonResponse({"success": False, "error": "quest_not_found"}, status=404)
    except Exception as e:
        logger.exception("Error starting quest")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ======================================================
# CANCEL QUEST
# ======================================================

@login_required
@require_POST
def cancel_quest(request):
    """
    Отменить квест (удаление или выключение).
    Я сделал мягко:
    - если есть поле active → выключаем
    - иначе удаляем
    """
    try:
        data = _get_request_data(request)
        quest_id = data.get("quest_id")

        if not quest_id:
            return JsonResponse({"success": False, "error": "quest_id_required"}, status=400)

        player = _player_for_request(request)
        quest = Quest.objects.get(id=quest_id, player=player)

        if hasattr(quest, "active"):
            quest.active = False
            quest.save()
        else:
            quest.delete()

        return JsonResponse({"success": True})

    except Quest.DoesNotExist:
        return JsonResponse({"success": False, "error": "quest_not_found"}, status=404)
    except Exception as e:
        logger.exception("Error canceling quest")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ======================================================
# COMPLETE QUEST
# ======================================================

@login_required
@require_POST
def complete_quest(request):
    """
    Завершение квеста кнопкой.
    Теперь:
    - проверяем что прогресс достигнут
    - иначе не даём завершить
    """
    try:
        data = _get_request_data(request)
        quest_id = data.get("quest_id")

        if not quest_id:
            return JsonResponse({"success": False, "error": "quest_id_required"}, status=400)

        player = _player_for_request(request)
        quest = Quest.objects.get(id=quest_id, player=player)

        if quest.completed:
            return JsonResponse({"success": True, "message": "already_completed", "quest": _serialize_quest_for_api(quest)})

        progress = _safe_int(getattr(quest, "progress", 0), 0)
        goal = _safe_int(getattr(quest, "goal", 1), 1)

        if progress < goal:
            return JsonResponse({
                "success": False,
                "error": "quest_not_ready",
                "message": "Quest is not ready to complete",
                "quest": _serialize_quest_for_api(quest),
            }, status=400)

        # Если в модели есть метод complete_quest — используем
        if hasattr(quest, "complete_quest") and callable(quest.complete_quest):
            quest.complete_quest()
        else:
            # fallback: просто помечаем как выполненный
            quest.completed = True
            quest.save()

        return JsonResponse({
            "success": True,
            "message": "Quest completed",
            "quest": _serialize_quest_for_api(quest),
            "rewards": {
                "xp": _safe_int(getattr(quest, "reward_xp", 0), 0),
                "currency": _safe_int(getattr(quest, "reward_currency", 0), 0),
                "skill_points": _safe_int(getattr(quest, "reward_skill_points", 0), 0),
            },
            "player": _serialize_player(player),
        })

    except Quest.DoesNotExist:
        return JsonResponse({"success": False, "error": "quest_not_found"}, status=404)
    except Exception as e:
        logger.exception("Error completing quest")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ======================================================
# QUEST PROGRESS UPDATE (HOOK)
# ======================================================

def update_quests_after_workout(player, exercise_type, reps, perfect_form=False):
    """
    Хук, который нужно вызывать после тренировки.
    """
    try:
        if not player:
            return

        # Только активные и не выполненные
        qs = Quest.objects.filter(player=player, completed=False)

        for quest in qs:
            # если есть метод add_progress — используем
            if hasattr(quest, "add_progress") and callable(quest.add_progress):
                completed = quest.add_progress(
                    exercise_type=exercise_type,
                    amount=reps,
                    perfect_rep=perfect_form,
                )

                if completed:
                    if hasattr(quest, "complete_quest") and callable(quest.complete_quest):
                        quest.complete_quest()
                    else:
                        quest.completed = True
                        quest.save()
            else:
                # fallback: если в модели нет add_progress — просто не ломаемся
                continue

    except Exception:
        logger.exception("update_quests_after_workout failed")
