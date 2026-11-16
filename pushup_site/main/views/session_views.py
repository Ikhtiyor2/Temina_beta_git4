# main/views/session_views.py (УПРОЩЕННАЯ ВЕРСИЯ)
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.middleware.csrf import get_token

from main.models import Player

logger = logging.getLogger(__name__)

# 🔴 СОЗДАЕМ ДЕКОРАТОРЫ ПРЯМО ЗДЕСЬ (самый простой способ)
from functools import wraps

def csrf_protect_api(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            csrf_token = request.headers.get('X-CSRFToken')
            
            if not csrf_token and request.body:
                try:
                    data = json.loads(request.body)
                    csrf_token = data.get('csrfmiddlewaretoken')
                except:
                    pass
            
            if not csrf_token or csrf_token != get_token(request):
                return JsonResponse({
                    "success": False,
                    "error": "csrf_validation_failed"
                }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view

def handle_api_exceptions(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.exception(f"API error: {e}")
            return JsonResponse({
                "success": False,
                "error": "server_error"
            }, status=500)
    
    return wrapped_view


@login_required
@require_POST
@csrf_protect_api
@handle_api_exceptions
def init_session(request):
    """
    Инициализация клиентской сессии
    """
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")
        user_agent = data.get("user_agent", "")
        
        logger.info(
            f"Session initialized: user={request.user.username}, session={session_id}"
        )
        
        # Создаем/обновляем игрока
        player, created = Player.objects.get_or_create(user=request.user)
        
        # Обновляем streak если нужно
        player.update_login_streak()
        player.save()
        
        return JsonResponse({
            "success": True,
            "session_id": session_id,
            "player_id": player.id,
            "csrf_token": get_token(request),
            "server_time": timezone.now().isoformat(),
        })
        
    except Exception as e:
        logger.exception("Error initializing session")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


@login_required
@require_POST
@csrf_protect_api
@handle_api_exceptions
def end_session(request):
    """
    Завершение клиентской сессии
    """
    try:
        data = json.loads(request.body)
        session_id = data.get("session_id")
        
        logger.info(
            f"Session ended: user={request.user.username}, session={session_id}"
        )
        
        return JsonResponse({
            "success": True,
            "message": "Session ended",
        })
        
    except Exception as e:
        logger.exception("Error ending session")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )