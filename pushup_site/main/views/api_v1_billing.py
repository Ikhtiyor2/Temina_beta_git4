"""
Billing API: статус подписки для клиента + вебхук RevenueCat.

Поток:
  1. Покупка проходит в приложении через RevenueCat SDK.
  2. RevenueCat шлёт вебхук на /api/v1/billing/rcat/ (с заголовком Authorization).
  3. Мы проверяем заголовок, по app_user_id находим User, дёргаем REST
     GET /subscribers/{id} и сохраняем канонический статус в Subscription.
  4. Клиент/бэкенд читают Subscription как источник правды.
"""
import hmac
import json
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from main.models import Subscription
from main.services.revenuecat import extract_entitlement_state, fetch_subscriber

logger = logging.getLogger(__name__)


def _subscription_payload(sub: Subscription) -> dict:
    return {
        "active": sub.is_active(),
        "status": sub.status,
        "entitlementId": sub.entitlement_id,
        "productId": sub.product_id,
        "store": sub.store,
        "currentPeriodEnd": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "autoRenewing": sub.auto_renewing,
    }


def _empty_payload() -> dict:
    return {
        "active": False,
        "status": Subscription.STATUS_EXPIRED,
        "entitlementId": "",
        "productId": "",
        "store": "",
        "currentPeriodEnd": None,
        "autoRenewing": False,
    }


@require_GET
def api_v1_subscription(request):
    """Текущий статус подписки авторизованного пользователя."""
    if not request.user.is_authenticated:
        return JsonResponse(
            {"ok": False, "error": "authentication_required"},
            status=401,
        )

    sub = Subscription.objects.filter(user=request.user).first()
    payload = _subscription_payload(sub) if sub else _empty_payload()
    return JsonResponse({"ok": True, "subscription": payload})


def _sync_from_revenuecat(user: User, app_user_id: str, event_id: str = "") -> Subscription:
    """Тянет канонический статус из RevenueCat REST и пишет его в Subscription."""
    entitlement_id = getattr(settings, "REVENUECAT_PRO_ENTITLEMENT", "pro")
    subscriber = fetch_subscriber(app_user_id)
    state = extract_entitlement_state(subscriber or {}, entitlement_id)

    sub, _ = Subscription.objects.get_or_create(user=user)
    sub.platform = "revenuecat"
    sub.app_user_id = app_user_id
    sub.entitlement_id = entitlement_id if state["active"] else sub.entitlement_id
    sub.product_id = state["product_id"] or sub.product_id
    sub.store = state["store"] or sub.store
    sub.current_period_end = state["expires_at"]
    if state["auto_renewing"] is not None:
        sub.auto_renewing = state["auto_renewing"]

    if state["active"]:
        sub.status = (
            Subscription.STATUS_ACTIVE
            if sub.auto_renewing or state["auto_renewing"] is None
            else Subscription.STATUS_CANCELED
        )
    else:
        sub.status = Subscription.STATUS_EXPIRED

    if event_id:
        sub.last_event_id = event_id
    sub.save()
    return sub


@csrf_exempt
@require_POST
def api_v1_billing_rcat(request):
    """
    Вебхук RevenueCat. Проверяем общий секрет в заголовке Authorization,
    затем по app_user_id подтягиваем канонический статус через REST.
    Всегда отвечаем быстро (200), чтобы RevenueCat не ретраил.
    """
    expected = getattr(settings, "REVENUECAT_WEBHOOK_AUTH", "")
    provided = request.headers.get("Authorization", "")
    if not expected or not hmac.compare_digest(provided, expected):
        logger.warning("RevenueCat webhook: невалидный Authorization")
        return HttpResponse("unauthorized", status=401)

    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    event = body.get("event", {}) or {}
    event_id = event.get("id", "") or ""
    event_type = event.get("type", "") or ""
    app_user_id = (
        event.get("app_user_id")
        or event.get("original_app_user_id")
        or ""
    )

    if not app_user_id:
        logger.warning("RevenueCat webhook %s без app_user_id", event_type)
        return JsonResponse({"ok": True})  # нечего обновлять, но 200

    user = User.objects.filter(pk=app_user_id).first()
    if user is None:
        # app_user_id может быть username, если так настроен клиент
        user = User.objects.filter(username=app_user_id).first()
    if user is None:
        logger.info("RevenueCat webhook: неизвестный app_user_id=%s", app_user_id)
        return JsonResponse({"ok": True})

    # Идемпотентность: тот же event id уже обработан
    existing = Subscription.objects.filter(user=user).first()
    if existing and event_id and existing.last_event_id == event_id:
        return JsonResponse({"ok": True, "duplicate": True})

    try:
        _sync_from_revenuecat(user, str(app_user_id), event_id=event_id)
    except Exception:  # noqa: BLE001 — вебхук всегда должен вернуть 200
        logger.exception("RevenueCat webhook: ошибка синхронизации для %s", app_user_id)

    return JsonResponse({"ok": True})
