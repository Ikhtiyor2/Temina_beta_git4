"""Проверка подписи Telegram Mini App initData и поиск/создание игрока."""
import hashlib
import hmac
import json
import time
import uuid
from typing import Optional, Tuple
from urllib.parse import parse_qsl

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from main.models import Player

INIT_DATA_MAX_AGE_SECONDS = 24 * 60 * 60


class TelegramAuthError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def verify_telegram_init_data(init_data: str, bot_token: str, now: Optional[float] = None) -> dict:
    """Возвращает объект user из initData. Иначе TelegramAuthError."""
    raw = (init_data or "").strip()
    token = (bot_token or "").strip()
    if not raw:
        raise TelegramAuthError("missing_init_data")
    if not token:
        raise TelegramAuthError("telegram_not_configured")

    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=False)
    data = {key: value for key, value in pairs}
    if len(data) != len(pairs):
        raise TelegramAuthError("bad_signature")
    received_hash = data.pop("hash", "")
    if len(received_hash) != 64:
        raise TelegramAuthError("bad_signature")

    check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
    calculated = hmac.new(secret, check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise TelegramAuthError("bad_signature")

    try:
        auth_date = int(data.get("auth_date") or 0)
    except (TypeError, ValueError):
        auth_date = 0
    current = time.time() if now is None else now
    if auth_date <= 0 or auth_date > current + 60 or current - auth_date > INIT_DATA_MAX_AGE_SECONDS:
        raise TelegramAuthError("stale")

    try:
        user = json.loads(data.get("user") or "")
    except (TypeError, json.JSONDecodeError):
        raise TelegramAuthError("missing_user")
    if not isinstance(user, dict) or user.get("id") in (None, ""):
        raise TelegramAuthError("missing_user")
    try:
        user["id"] = int(user["id"])
    except (TypeError, ValueError):
        raise TelegramAuthError("missing_user")
    if user["id"] <= 0:
        raise TelegramAuthError("missing_user")
    return user


def display_name_from_telegram(tg_user: dict) -> str:
    first = str(tg_user.get("first_name") or "").strip()
    last = str(tg_user.get("last_name") or "").strip()
    full = f"{first} {last}".strip()
    if full:
        return full[:120]
    username = str(tg_user.get("username") or "").strip()
    if username:
        return username[:120]
    return f"tg_{tg_user['id']}"[:120]


def apply_telegram_profile(player: Player, tg_user: dict) -> None:
    """Каждый вход Mini App перезаписывает имя и фото из initData."""
    user = player.user
    first = str(tg_user.get("first_name") or "")[:150]
    last = str(tg_user.get("last_name") or "")[:150]
    changed = []
    if user.first_name != first:
        user.first_name = first
        changed.append("first_name")
    if user.last_name != last:
        user.last_name = last
        changed.append("last_name")
    if changed:
        user.save(update_fields=changed)

    player.telegram_username = str(tg_user.get("username") or "")[:64]
    player.display_name = display_name_from_telegram(tg_user)
    photo = str(tg_user.get("photo_url") or "").strip()
    if photo.startswith("https://") and len(photo) <= 512:
        player.avatar_url = photo
    elif not photo:
        player.avatar_url = ""


def get_or_create_telegram_player(tg_user: dict) -> Tuple[Player, bool]:
    """Находит игрока по telegram_id или создаёт User без пароля. Второй флаг — новый аккаунт."""
    telegram_id = int(tg_user["id"])
    player = Player.objects.select_related("user").filter(telegram_id=telegram_id).first()
    created = player is None
    if player is None:
        try:
            with transaction.atomic():
                # A matching username does not prove ownership of an account.
                username = f"tg_{telegram_id}"
                if User.objects.filter(username=username).exists():
                    username += "_" + uuid.uuid4().hex
                user = User.objects.create_user(username=username, password=None)
                player = Player.objects.create(user=user, telegram_id=telegram_id)
        except IntegrityError:
            # A concurrent first login may have created the Telegram identity.
            player = Player.objects.select_related("user").filter(telegram_id=telegram_id).first()
            if player is None:
                raise
            created = False

    if not player.user.is_active:
        raise TelegramAuthError("account_disabled")
    apply_telegram_profile(player, tg_user)
    return player, created
