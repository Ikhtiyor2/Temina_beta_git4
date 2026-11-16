from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from main.models import Player, Quest
from main.quest_i18n import localize_quest_text
from main.quest_manager import QuestManager
from main.views.api_v1_helpers import json_error, request_lang, require_authenticated_json


def _player(request):
    player, _ = Player.objects.get_or_create(user=request.user)
    manager = QuestManager(player)
    if Quest.objects.filter(player=player).count() == 0:
        manager.create_initial_quests()
    else:
        manager.generate_daily_quests()
    manager.generate_weekly_quests()
    return player


def _quest_status(quest: Quest) -> str:
    if quest.completed:
        return "claimed"
    if int(quest.progress or 0) >= int(quest.goal or 1):
        return "completed_unclaimed"
    return "active"


def _serialize_quest(quest: Quest, lang: str = "ru") -> dict:
    title, description = localize_quest_text(quest, lang)
    return {
        "id": str(quest.id),
        "title": title,
        "description": description,
        "progressCurrent": int(quest.progress or 0),
        "progressTarget": int(quest.goal or 1),
        "rewardXp": int(quest.reward_xp or 0),
        "status": _quest_status(quest),
        "type": "daily" if quest.is_daily else "weekly",
        "questType": quest.quest_type,
    }


@require_GET
def api_v1_quests(request):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    quest_type = (request.GET.get("type") or "daily").lower()
    if quest_type not in {"daily", "weekly"}:
        return json_error("Invalid quest type", status=400, code="invalid_quest_type")
    lang = request_lang(request)
    player = _player(request)
    quests = Quest.objects.filter(player=player, is_daily=(quest_type == "daily")).order_by("-created_at")
    return JsonResponse({"type": quest_type, "quests": [_serialize_quest(q, lang) for q in quests]})


@require_GET
def api_v1_quest_detail(request, quest_id: int):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    lang = request_lang(request)
    player = _player(request)
    try:
        quest = Quest.objects.get(id=quest_id, player=player)
    except Quest.DoesNotExist:
        return json_error("Quest not found", status=404, code="quest_not_found")
    return JsonResponse({"quest": _serialize_quest(quest, lang)})


@require_POST
def api_v1_quest_start(request, quest_id: int):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    lang = request_lang(request)
    player = _player(request)
    try:
        quest = Quest.objects.get(id=quest_id, player=player)
    except Quest.DoesNotExist:
        return json_error("Quest not found", status=404, code="quest_not_found")
    if quest.completed:
        return json_error("Quest is already claimed", status=400, code="quest_claimed")
    return JsonResponse({"quest": _serialize_quest(quest, lang)})


@require_POST
def api_v1_quest_claim(request, quest_id: int):
    auth_error = require_authenticated_json(request)
    if auth_error:
        return auth_error
    lang = request_lang(request)
    player = _player(request)
    try:
        with transaction.atomic():
            quest = Quest.objects.select_for_update().get(id=quest_id, player=player)
            if quest.completed:
                return JsonResponse({"quest": _serialize_quest(quest, lang)})
            if int(quest.progress or 0) < int(quest.goal or 1):
                return json_error("Quest is not completed yet", status=400, code="quest_not_ready")
            streak_bonus = 0
            if quest.is_daily and int(player.login_streak or 0) >= 7:
                streak_bonus = int(quest.reward_xp or 0) // 4
            quest.complete_quest()
            if streak_bonus > 0:
                player.add_exp(streak_bonus)
                player.save()
    except Quest.DoesNotExist:
        return json_error("Quest not found", status=404, code="quest_not_found")
    quest.refresh_from_db()
    return JsonResponse({"quest": _serialize_quest(quest, lang)})
