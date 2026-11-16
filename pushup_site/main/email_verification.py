"""
Soft email verification helpers.

Users can use the app without confirming; we still send a link and track
Player.email_verified. Tokens are signed (no DB row) and expire after 48h.
"""
from __future__ import annotations

import logging

from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

_SALT = "temina.email-verify"
_MAX_AGE_SECONDS = 48 * 3600


def _signer() -> TimestampSigner:
    return TimestampSigner(salt=_SALT)


def make_email_verify_token(user) -> str:
    email = (user.email or "").strip().lower()
    return _signer().sign(f"{user.pk}:{email}")


def parse_email_verify_token(token: str) -> tuple[int, str] | None:
    """Return (user_id, email) or None if invalid/expired."""
    try:
        raw = _signer().unsign(token, max_age=_MAX_AGE_SECONDS)
    except SignatureExpired:
        return None
    except BadSignature:
        return None
    try:
        user_id_str, email = raw.split(":", 1)
        return int(user_id_str), email.strip().lower()
    except (ValueError, TypeError):
        return None


def public_base_url() -> str:
    base = (getattr(settings, "PUBLIC_BASE_URL", None) or "").strip().rstrip("/")
    if base:
        return base
    if settings.DEBUG:
        return "http://127.0.0.1:8000"
    return "https://temina.fit"


def build_verify_url(token: str) -> str:
    # Manual path + quote: signed tokens contain ":" and must survive email clients.
    return f"{public_base_url()}/verify-email/{quote(token, safe='')}/"


def send_verification_email(user) -> tuple[bool, str]:
    """
    Send verification email via Django EMAIL_* (Resend SMTP etc.).
    Returns (ok, error_message). Soft mode: callers should not fail registration.
    """
    email = (user.email or "").strip()
    if not email:
        return False, "no_email"

    if not (getattr(settings, "EMAIL_HOST_PASSWORD", "") or "").strip():
        logger.error("EMAIL_HOST_PASSWORD empty — cannot send via Resend")
        return False, "email_not_configured"

    token = make_email_verify_token(user)
    verify_url = build_verify_url(token)
    context = {
        "username": user.username,
        "verify_url": verify_url,
        "hours": _MAX_AGE_SECONDS // 3600,
    }
    subject = "Подтвердите email в Temina"
    text_body = render_to_string("email/verify_email.txt", context)
    html_body = render_to_string("email/verify_email.html", context)
    from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        "Temina <hello@noreply.temina.fit>",
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=[email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        return True, ""
    except Exception as exc:
        logger.exception(
            "Failed to send verification email to user_id=%s from=%s",
            user.pk,
            from_email,
        )
        return False, str(exc)[:200]


def mark_email_verified(user) -> None:
    from main.models import Player

    player, _ = Player.objects.get_or_create(user=user)
    if not player.email_verified:
        player.email_verified = True
        player.save(update_fields=["email_verified"])
