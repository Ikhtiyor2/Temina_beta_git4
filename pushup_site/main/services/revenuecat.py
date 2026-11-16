"""
Клиент RevenueCat REST API (v1) для серверной сверки статуса подписки.

Используется stdlib urllib, чтобы не тянуть новую зависимость.
Документация: после любого вебхука рекомендуется дёрнуть GET /subscribers/{id}
и взять канонический статус entitlements, а не парсить тело каждого события.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone as dt_timezone
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.revenuecat.com/v1"


def _parse_rc_datetime(value: Optional[str]) -> Optional[datetime]:
    """RevenueCat отдаёт даты в ISO8601 c 'Z' (UTC)."""
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dt_timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def fetch_subscriber(app_user_id: str, timeout: float = 5.0) -> Optional[dict]:
    """
    Возвращает объект subscriber из RevenueCat или None при ошибке.
    """
    api_key = getattr(settings, "REVENUECAT_SECRET_API_KEY", "")
    if not api_key or not app_user_id:
        logger.warning("RevenueCat: нет API ключа или app_user_id")
        return None

    url = f"{_BASE_URL}/subscribers/{urllib.parse.quote(str(app_user_id), safe='')}"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "X-Platform": "android",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return payload.get("subscriber")
    except urllib.error.HTTPError as e:
        logger.warning("RevenueCat HTTP %s для %s", e.code, app_user_id)
        return None
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        logger.warning("RevenueCat недоступен для %s: %s", app_user_id, e)
        return None


def extract_entitlement_state(subscriber: dict, entitlement_id: str) -> dict:
    """
    Достаёт из subscriber состояние конкретного entitlement.

    Возвращает dict:
        active: bool — действует ли прямо сейчас (по expires_date)
        expires_at: datetime | None
        product_id: str
        store: str
        auto_renewing: bool | None
    """
    result = {
        "active": False,
        "expires_at": None,
        "product_id": "",
        "store": "",
        "auto_renewing": None,
    }
    if not subscriber:
        return result

    entitlements = subscriber.get("entitlements") or {}
    ent = entitlements.get(entitlement_id)
    if not ent:
        return result

    expires_at = _parse_rc_datetime(ent.get("expires_date"))
    product_id = ent.get("product_identifier", "") or ""
    result["expires_at"] = expires_at
    result["product_id"] = product_id
    # entitlement без expires_date (lifetime) считаем активным
    result["active"] = expires_at is None or expires_at > datetime.now(dt_timezone.utc)

    subscriptions = subscriber.get("subscriptions") or {}
    sub = subscriptions.get(product_id) or {}
    result["store"] = sub.get("store", "") or ""
    if "unsubscribe_detected_at" in sub:
        result["auto_renewing"] = sub.get("unsubscribe_detected_at") is None

    return result


def has_active_entitlement(app_user_id: str, entitlement_id: Optional[str] = None) -> bool:
    """Живая проверка через REST: есть ли активный entitlement у пользователя."""
    entitlement_id = entitlement_id or getattr(settings, "REVENUECAT_PRO_ENTITLEMENT", "pro")
    subscriber = fetch_subscriber(app_user_id)
    if not subscriber:
        return False
    return extract_entitlement_state(subscriber, entitlement_id)["active"]
