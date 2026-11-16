"""Простой rate limit на базе Django cache (без внешних зависимостей)."""
from django.core.cache import cache
from django.http import JsonResponse


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def is_rate_limited(request, scope: str, limit: int = 10, window_seconds: int = 60) -> bool:
    """True, если лимит исчерпан."""
    key = f"ratelimit:{scope}:{client_ip(request)}"
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, window_seconds)
        return False
    return count > limit


def rate_limit_json_response():
    return JsonResponse(
        {
            "ok": False,
            "error": "rate_limit_exceeded",
            "message": "Слишком много запросов. Подождите минуту.",
        },
        status=429,
    )
