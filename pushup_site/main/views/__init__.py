# main/views/__init__.py
"""
Декораторы для всех views.
"""
import json
import logging
from functools import wraps

from django.http import JsonResponse
from django.middleware.csrf import get_token

logger = logging.getLogger(__name__)


def csrf_protect_api(view_func):
    """Декоратор для проверки CSRF"""
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
    """Декоратор для обработки исключений"""
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