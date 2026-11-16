from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_gemini_config() -> dict[str, str]:
    api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"

    if not api_key:
        raise ImproperlyConfigured(
            "GEMINI_API_KEY is empty. Set GEMINI_API_KEY in environment or .env."
        )

    return {
        "api_key": api_key,
        "model": model,
    }
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_gemini_config() -> dict[str, str]:
    api_key = getattr(settings, "GEMINI_API_KEY", "").strip()
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"

    if not api_key:
        raise ImproperlyConfigured(
            "GEMINI_API_KEY is empty. Set GEMINI_API_KEY in environment or .env."
        )

    return {
        "api_key": api_key,
        "model": model,
    }
