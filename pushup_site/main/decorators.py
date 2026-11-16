# main/decorators.py
"""
Кастомные декораторы для Django views.
"""
import json
import logging
from functools import wraps

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.crypto import constant_time_compare

logger = logging.getLogger(__name__)


def csrf_protect_api(view_func):
    """
    Кастомный декоратор для проверки CSRF через заголовки X-CSRFToken.
    Поддерживает JSON и form-data.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Проверяем только модифицирующие методы
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            
            # 1. Пытаемся получить из заголовков
            csrf_token_header = (
                request.headers.get('X-CSRFToken') or 
                request.headers.get('X-CSRF-Token') or
                request.headers.get('X-Csrf-Token')
            )
            
            # 2. Пытаемся получить из POST данных (form-data)
            csrf_token_post = request.POST.get('csrfmiddlewaretoken')
            
            # 3. Пытаемся получить из JSON body
            csrf_token_json = None
            if request.body:
                try:
                    # Проверяем content-type
                    content_type = request.content_type or ''
                    if 'application/json' in content_type:
                        data = json.loads(request.body)
                        csrf_token_json = data.get('csrfmiddlewaretoken') or data.get('csrf_token')
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                    # Если не JSON, игнорируем
                    pass
            
            # Объединяем все источники
            csrf_token = csrf_token_header or csrf_token_post or csrf_token_json
            
            # Получаем валидный токен из сессии
            valid_token = get_token(request)
            
            # Проверяем CSRF токен
            if not csrf_token or not constant_time_compare(csrf_token, valid_token):
                logger.warning(
                    "CSRF validation failed for %s. Method: %s, User: %s",
                    request.path,
                    request.method,
                    request.user.username if request.user.is_authenticated else "Anonymous",
                )
                return JsonResponse(
                    {
                        "success": False,
                        "error": "csrf_validation_failed",
                        "message": "CSRF token missing or invalid",
                        "hint": "Include X-CSRFToken header or csrfmiddlewaretoken in body"
                    },
                    status=403
                )
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def handle_api_exceptions(view_func):
    """
    Обработчик исключений для API endpoints.
    Логирует ошибки и возвращает JSON response.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.exception(f"API error in {view_func.__name__}: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "server_error",
                    "message": str(e)[:200]  # Ограничиваем длину для безопасности
                },
                status=500
            )
    
    return wrapped_view


def api_login_required(view_func):
    """
    Декоратор для API, возвращающий JSON при отсутствии авторизации.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    "success": False,
                    "error": "authentication_required",
                    "message": "You must be logged in to access this resource"
                },
                status=401
            )
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def subscription_required(view_func):
    """
    Декоратор для эндпоинтов, доступных только по активной подписке (Temina Pro).
    Источник правды — модель Subscription (обновляется вебхуком RevenueCat).
    Возвращает 402 Payment Required, если подписки нет или она истекла.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    "success": False,
                    "error": "authentication_required",
                    "message": "You must be logged in to access this resource",
                },
                status=401,
            )

        from main.models import Subscription

        sub = Subscription.objects.filter(user=request.user).first()
        if not sub or not sub.is_active():
            return JsonResponse(
                {
                    "success": False,
                    "error": "subscription_required",
                    "message": "Эта функция доступна по подписке Temina Pro",
                },
                status=402,
            )
        return view_func(request, *args, **kwargs)

    return wrapped_view


def validate_request_body(required_fields=None, optional_fields=None):
    """
    Валидатор полей в теле запроса.
    
    Args:
        required_fields: Список обязательных полей
        optional_fields: Список опциональных полей
    """
    if required_fields is None:
        required_fields = []
    if optional_fields is None:
        optional_fields = []
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if request.method in ('POST', 'PUT', 'PATCH'):
                try:
                    data = json.loads(request.body) if request.body else {}
                    
                    # Проверяем обязательные поля
                    missing_fields = []
                    for field in required_fields:
                        if field not in data:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        return JsonResponse(
                            {
                                "success": False,
                                "error": "missing_fields",
                                "message": f"Missing required fields: {', '.join(missing_fields)}",
                                "required_fields": required_fields,
                                "optional_fields": optional_fields
                            },
                            status=400
                        )
                    
                    # Добавляем validated_data в request
                    request.validated_data = {
                        field: data.get(field) 
                        for field in required_fields + optional_fields 
                        if field in data
                    }
                    
                except json.JSONDecodeError:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "invalid_json",
                            "message": "Invalid JSON in request body"
                        },
                        status=400
                    )
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    
    return decorator


def log_request(view_func):
    """
    Логирует входящие запросы и исходящие ответы.
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Логируем входящий запрос
        logger.info(
            f"Request: {request.method} {request.path} | "
            f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'} | "
            f"IP: {request.META.get('REMOTE_ADDR', 'Unknown')}"
        )
        
        # Вызываем view функцию
        response = view_func(request, *args, **kwargs)
        
        # Логируем ответ
        if hasattr(response, 'status_code'):
            logger.info(
                f"Response: {request.method} {request.path} | "
                f"Status: {response.status_code} | "
                f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}"
            )
        
        return response
    
    return wrapped_view