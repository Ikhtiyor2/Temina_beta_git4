# main/views/player_views.py
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required

from main.models import Player

# 🔴 ИСПРАВЛЯЕМ ИМПОРТ
try:
    from decorators import csrf_protect_api, handle_api_exceptions
except ImportError:
    from main.decorators import csrf_protect_api, handle_api_exceptions

logger = logging.getLogger(__name__)
# ======================================================
# PLAYER PROFILE
# ======================================================

@login_required
@require_GET
def get_player_profile(request):
    """
    Возвращает профиль игрока.
    """

    try:
        player, _ = Player.objects.get_or_create(user=request.user)

        return JsonResponse({
            "success": True,
            "player": {
                "username": player.user.username,
                "level": player.level,
                "exp": player.exp,
                "exp_to_level": player.exp_to_level,
                "skill_points": player.skill_points,
                "currency": player.currency,
                "fatigue": player.fatigue,
                "login_streak": player.login_streak,
            },
            "skills": {
                "strength": player.strength,
                "stamina": player.stamina,
                "agility": player.agility,
                "technique": player.technique,
            }
        })

    except Exception as e:
        logger.exception("Error loading player profile")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# UPGRADE SKILL
# ======================================================

@login_required
@require_POST
def upgrade_skill(request):
    """
    Улучшение навыка игрока.
    """

    try:
        data = json.loads(request.body)
        skill = data.get("skill")

        if not skill:
            return JsonResponse(
                {"success": False, "error": "skill_required"},
                status=400,
            )

        player = Player.objects.get(user=request.user)

        if not player.upgrade_skill(skill):
            return JsonResponse(
                {"success": False, "error": "not_enough_skill_points"},
                status=400,
            )

        player.save()

        return JsonResponse({
            "success": True,
            "skill": skill,
            "new_value": getattr(player, skill),
            "skill_points": player.skill_points,
        })

    except Exception as e:
        logger.exception("Error upgrading skill")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# ADD / REMOVE CURRENCY (ADMIN / SYSTEM)
# ======================================================

@login_required
@require_POST
def add_currency(request):
    """
    Добавление валюты игроку — только для staff (админ/системные операции).
    Обычные игроки получают валюту через квесты и награды на сервере.
    """
    if not request.user.is_staff:
        return JsonResponse(
            {"success": False, "error": "forbidden", "message": "Недостаточно прав"},
            status=403,
        )

    try:
        data = json.loads(request.body)
        amount = int(data.get("amount", 0))

        if amount <= 0:
            return JsonResponse(
                {"success": False, "error": "invalid_amount"},
                status=400,
            )
        # Лимит за один запрос, чтобы нельзя было накрутить валюту произвольно
        if amount > 1000:
            return JsonResponse(
                {"success": False, "error": "amount_too_high", "message": "Максимум 1000 за запрос"},
                status=400,
            )

        player = Player.objects.get(user=request.user)
        player.currency += amount
        player.save()

        return JsonResponse({
            "success": True,
            "currency": player.currency,
        })

    except Exception as e:
        logger.exception("Error adding currency")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


# ======================================================
# LOGIN STREAK UPDATE (HOOK)
# ======================================================

@login_required
@require_POST
def update_login_streak(request):
    """
    Обновление streak входов.
    Обычно вызывается при логине.
    """

    try:
        player, _ = Player.objects.get_or_create(user=request.user)
        player.update_login_streak()
        player.save()

        return JsonResponse({
            "success": True,
            "login_streak": player.login_streak,
        })

    except Exception as e:
        logger.exception("Error updating login streak")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )
