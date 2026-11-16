"""
JSON API авторизации для нативного клиента (Android).
Сессия Django + cookie sessionid; CSRF через X-CSRFToken (см. /api/csrf-token/).
Soft email verification: вход разрешён без подтверждения; флаг emailVerified в payload.
"""
import json

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from main.email_verification import (
    mark_email_verified,
    parse_email_verify_token,
    send_verification_email,
)
from main.forms import RegistrationForm
from main.models import FitnessAssessment, Player
from main.rate_limit import is_rate_limited, rate_limit_json_response


def _user_has_assessment(user) -> bool:
    return FitnessAssessment.objects.filter(user=user).exists()


def _email_verified(user) -> bool:
    try:
        return bool(user.player.email_verified)
    except Player.DoesNotExist:
        return False


def _user_payload(user):
    try:
        player = user.player
    except Player.DoesNotExist:
        player = None
    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email or "",
        "first_name": user.first_name or "",
        "displayName": (player.display_name if player else "") or user.first_name or user.username,
        "avatarUrl": (player.avatar_url if player else "") or None,
        "telegramUsername": (player.telegram_username if player else "") or "",
        "hasAssessment": _user_has_assessment(user),
        "emailVerified": _email_verified(user),
    }


@require_GET
def api_auth_me(request):
    """Проверка сессии (cookie sessionid)."""
    if request.user.is_authenticated:
        return JsonResponse(
            {"ok": True, "authenticated": True, "user": _user_payload(request.user)}
        )
    return JsonResponse({"ok": True, "authenticated": False})


@require_POST
def api_auth_login(request):
    if is_rate_limited(request, "auth_login", limit=10, window_seconds=60):
        return rate_limit_json_response()

    try:
        data = json.loads(request.body.decode("utf-8") if request.body else "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"ok": False, "error": "invalid_credentials"}, status=401)

    login(request, user)

    player, _ = Player.objects.get_or_create(user=user)
    player.update_login_streak()
    player.save()
    try:
        from main.quest_manager import QuestManager

        QuestManager(player).complete_daily_login()
    except Exception:
        pass

    return JsonResponse({"ok": True, "user": _user_payload(user)})


@require_POST
def api_auth_telegram(request):
    """Вход в Mini App по подписанному initData. Сессия та же, что у почтового входа."""
    if is_rate_limited(request, "auth_telegram", limit=10, window_seconds=60):
        return rate_limit_json_response()

    token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
    if not token:
        return JsonResponse({"ok": False, "error": "telegram_not_configured"}, status=503)

    try:
        data = json.loads(request.body.decode("utf-8") if request.body else "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)
    init_data = data.get("initData") or data.get("init_data") or ""
    if not isinstance(init_data, str):
        return JsonResponse({"ok": False, "error": "invalid_init_data"}, status=400)
    init_data = init_data.strip()
    if not init_data:
        return JsonResponse({"ok": False, "error": "missing_init_data"}, status=400)

    from main.telegram_auth import TelegramAuthError, get_or_create_telegram_player, verify_telegram_init_data

    try:
        tg_user = verify_telegram_init_data(init_data, token)
        player, is_new = get_or_create_telegram_player(tg_user)
    except TelegramAuthError as exc:
        status = 503 if exc.code == "telegram_not_configured" else 401
        if exc.code == "missing_init_data":
            status = 400
        return JsonResponse({"ok": False, "error": exc.code}, status=status)

    player.update_login_streak()
    player.save()
    try:
        from main.quest_manager import QuestManager

        QuestManager(player).complete_daily_login()
    except Exception:
        pass

    login(request, player.user)
    return JsonResponse({"ok": True, "user": _user_payload(player.user), "isNew": is_new})


@require_POST
def api_auth_register(request):
    if is_rate_limited(request, "auth_register", limit=5, window_seconds=60):
        return rate_limit_json_response()

    if request.user.is_authenticated:
        return JsonResponse(
            {"ok": True, "user": _user_payload(request.user), "already_logged_in": True}
        )

    try:
        data = json.loads(request.body.decode("utf-8") if request.body else "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    form = RegistrationForm(
        data={
            "username": data.get("username") or "",
            "email": data.get("email") or "",
            "first_name": data.get("first_name") or "",
            "password1": data.get("password1") or data.get("password") or "",
            "password2": data.get("password2") or data.get("password") or "",
        }
    )

    if not form.is_valid():
        errors = {k: [str(x) for x in v] for k, v in form.errors.items()}
        return JsonResponse({"ok": False, "error": "validation_error", "errors": errors}, status=400)

    user = form.save()
    player, _ = Player.objects.get_or_create(user=user)
    player.email_verified = False
    player.update_login_streak()
    player.save()
    login(request, user)
    try:
        from main.quest_manager import QuestManager

        QuestManager(player).complete_daily_login()
    except Exception:
        pass

    email_sent, _send_err = send_verification_email(user)

    return JsonResponse(
        {
            "ok": True,
            "user": _user_payload(user),
            "emailSent": email_sent,
            "needsEmailVerification": True,
        }
    )


@require_POST
def api_auth_logout(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_POST
def api_auth_resend_verification(request):
    """Повторная отправка письма (soft). Требует сессию."""
    if is_rate_limited(request, "auth_resend_verify", limit=3, window_seconds=60):
        return rate_limit_json_response()

    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "not_authenticated"}, status=401)

    user = request.user
    if not (user.email or "").strip():
        return JsonResponse({"ok": False, "error": "no_email"}, status=400)

    if _email_verified(user):
        return JsonResponse(
            {"ok": True, "alreadyVerified": True, "user": _user_payload(user)}
        )

    sent, send_err = send_verification_email(user)
    if not sent:
        msg = "Не удалось отправить письмо. "
        if send_err in ("email_not_configured", "no_email"):
            msg += "Почта на сервере не настроена."
        elif send_err:
            # Short hint for ops; avoid dumping huge SMTP traces to the client.
            msg += "Проверьте DEFAULT_FROM_EMAIL=@noreply.temina.fit и логи Django."
        else:
            msg += "Попробуйте позже."
        return JsonResponse(
            {
                "ok": False,
                "error": "send_failed",
                "message": msg,
                "detail": send_err or "",
            },
            status=503,
        )
    return JsonResponse({"ok": True, "emailSent": True, "user": _user_payload(user)})


@require_http_methods(["GET", "POST"])
def api_auth_verify_email(request):
    """
    Подтверждение по токену (JSON). Soft: не требует сессии.
    GET/POST ?token=... или JSON body {"token": "..."}.
    """
    if is_rate_limited(request, "auth_verify_email", limit=20, window_seconds=60):
        return rate_limit_json_response()

    token = (request.GET.get("token") or "").strip()
    if not token and request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8") if request.body else "{}")
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)
        token = (data.get("token") or "").strip()

    if not token:
        return JsonResponse({"ok": False, "error": "missing_token"}, status=400)

    parsed = parse_email_verify_token(token)
    if parsed is None:
        return JsonResponse(
            {
                "ok": False,
                "error": "invalid_or_expired_token",
                "message": "Ссылка устарела или недействительна.",
            },
            status=400,
        )

    user_id, email = parsed
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "error": "user_not_found"}, status=404)

    current = (user.email or "").strip().lower()
    if current != email:
        return JsonResponse(
            {
                "ok": False,
                "error": "email_mismatch",
                "message": "Email аккаунта изменился. Запросите новое письмо.",
            },
            status=400,
        )

    mark_email_verified(user)
    return JsonResponse({"ok": True, "emailVerified": True, "user": _user_payload(user)})


@require_GET
def verify_email_page(request, token: str):
    """HTML-страница по ссылке из письма."""
    parsed = parse_email_verify_token(token)
    if parsed is None:
        return render(
            request,
            "auth/email_verified.html",
            {
                "ok": False,
                "message": "Ссылка устарела или недействительна. Запросите новое письмо в приложении.",
            },
            status=400,
        )

    user_id, email = parsed
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return render(
            request,
            "auth/email_verified.html",
            {"ok": False, "message": "Пользователь не найден."},
            status=404,
        )

    current = (user.email or "").strip().lower()
    if current != email:
        return render(
            request,
            "auth/email_verified.html",
            {
                "ok": False,
                "message": "Email аккаунта изменился. Запросите новое письмо в приложении.",
            },
            status=400,
        )

    mark_email_verified(user)
    return render(
        request,
        "auth/email_verified.html",
        {"ok": True, "email": user.email},
    )
