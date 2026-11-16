"""Cloudflare Turnstile: тихая проверка на форме регистрации.

Виджет в режиме interaction-only почти никому не показывает галочку.
Сервер принимает регистрацию только после siteverify.
"""
import json
import logging
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
_MAX_TOKEN_LEN = 2048

_MESSAGES = {
    "failed": {
        "ru": "Не удалось подтвердить браузер. Обновите страницу и попробуйте ещё раз.",
        "en": "We couldn't confirm this browser. Refresh the page and try again.",
        "uz": "Brauzerni tasdiqlab bo'lmadi. Sahifani yangilang va qayta urinib ko'ring.",
    },
    "unavailable": {
        "ru": "Регистрация временно недоступна.",
        "en": "Sign-up is temporarily unavailable.",
        "uz": "Ro'yxatdan o'tish vaqtincha yopiq.",
    },
}


def page_lang(request) -> str:
    lang = request.COOKIES.get("temina_lang", "ru")
    if lang not in ("ru", "en", "uz"):
        return "ru"
    return lang


def captcha_message(lang: str, code: str) -> str:
    bucket = _MESSAGES.get(code) or _MESSAGES["failed"]
    return bucket.get(lang) or bucket["ru"]


def turnstile_keys() -> tuple[str, str]:
    site = (getattr(settings, "TURNSTILE_SITE_KEY", "") or "").strip()
    secret = (getattr(settings, "TURNSTILE_SECRET_KEY", "") or "").strip()
    return site, secret


def turnstile_configured() -> bool:
    site, secret = turnstile_keys()
    return bool(site and secret)


def registration_captcha():
    """Ключ для виджета и флаг «форма закрыта».

    Оба ключа заданы — виджет и проверка.
    Ключей нет и DEBUG — локальная регистрация без капчи.
    Ключей нет на проде — регистрацию не открываем.
    """
    site, _secret = turnstile_keys()
    if turnstile_configured():
        return site, False
    return "", not settings.DEBUG


def verify_turnstile(token: str) -> bool:
    """True только если Cloudflare подтвердил токен."""
    _site, secret = turnstile_keys()
    token = (token or "").strip()
    if not secret or not token or len(token) > _MAX_TOKEN_LEN:
        return False

    payload = urlencode({"secret": secret, "response": token}).encode()
    request = Request(SITEVERIFY_URL, data=payload, method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        logger.warning("Turnstile siteverify failed", exc_info=True)
        return False
    return bool(body.get("success"))
