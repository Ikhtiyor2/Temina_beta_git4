"""In-app support chat API (user ↔ staff)."""

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from main.models import Player, SupportMessage, SupportThread
from main.views.api_v1_helpers import json_error, parse_json_body, require_authenticated_json

MAX_BODY_LEN = 4000
MAX_SUBJECT_LEN = 200
VALID_CATEGORIES = {
    SupportThread.CATEGORY_GENERAL,
    SupportThread.CATEGORY_TECHNICAL,
    SupportThread.CATEGORY_BILLING,
    SupportThread.CATEGORY_ACCOUNT,
}

WELCOME_MESSAGE = (
    "Здравствуйте! Мы получили ваше обращение. "
    "Команда Temina ответит здесь — обычно в течение рабочего дня."
)


def _me(request) -> Player:
    player, _ = Player.objects.get_or_create(user=request.user)
    return player


def _iso(dt) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _serialize_message(msg: SupportMessage) -> dict:
    return {
        "id": msg.id,
        "senderType": msg.sender_type,
        "body": msg.body,
        "createdAt": _iso(msg.created_at),
    }


def _serialize_thread(thread: SupportThread, *, include_messages: bool = False) -> dict:
    preview = ""
    last = thread.messages.order_by("-created_at").first()
    if last:
        preview = last.body[:160]
    payload = {
        "id": thread.id,
        "subject": thread.subject,
        "category": thread.category,
        "status": thread.status,
        "unreadByUser": thread.unread_by_user,
        "lastMessageAt": _iso(thread.last_message_at),
        "createdAt": _iso(thread.created_at),
        "updatedAt": _iso(thread.updated_at),
        "preview": preview,
    }
    if include_messages:
        msgs = thread.messages.order_by("created_at")
        payload["messages"] = [_serialize_message(m) for m in msgs]
    return payload


def _get_owned_thread(me: Player, thread_id: int) -> SupportThread | JsonResponse:
    try:
        return SupportThread.objects.get(pk=thread_id, player=me)
    except SupportThread.DoesNotExist:
        return json_error("Thread not found", status=404, code="not_found")


@require_GET
def api_v1_support_threads_list(request):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    threads = SupportThread.objects.filter(player=me).prefetch_related("messages")[:50]
    return JsonResponse(
        {
            "threads": [_serialize_thread(t) for t in threads],
            "unreadTotal": sum(t.unread_by_user for t in threads),
        }
    )


@require_POST
def api_v1_support_threads_create(request):
    err = require_authenticated_json(request)
    if err:
        return err
    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None

    subject = (body.get("subject") or "").strip()
    message = (body.get("body") or body.get("message") or "").strip()
    category = (body.get("category") or SupportThread.CATEGORY_GENERAL).strip().lower()

    if not subject:
        return json_error("subject is required", status=400, code="invalid_subject")
    if len(subject) > MAX_SUBJECT_LEN:
        return json_error("subject is too long", status=400, code="invalid_subject")
    if not message:
        return json_error("body is required", status=400, code="invalid_body")
    if len(message) > MAX_BODY_LEN:
        return json_error("body is too long", status=400, code="invalid_body")
    if category not in VALID_CATEGORIES:
        return json_error("invalid category", status=400, code="invalid_category")

    me = _me(request)
    now = timezone.now()
    with transaction.atomic():
        thread = SupportThread.objects.create(
            player=me,
            subject=subject,
            category=category,
            status=SupportThread.STATUS_WAITING_STAFF,
            last_message_at=now,
            unread_by_user=1,
        )
        SupportMessage.objects.create(
            thread=thread,
            sender_type=SupportMessage.SENDER_USER,
            sender_user=request.user,
            body=message,
        )
        SupportMessage.objects.create(
            thread=thread,
            sender_type=SupportMessage.SENDER_SYSTEM,
            body=WELCOME_MESSAGE,
        )

    thread = SupportThread.objects.prefetch_related("messages").get(pk=thread.pk)
    return JsonResponse(_serialize_thread(thread, include_messages=True), status=201)


@require_http_methods(["GET"])
def api_v1_support_thread_detail(request, thread_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    thread = _get_owned_thread(me, thread_id)
    if isinstance(thread, JsonResponse):
        return thread

    if thread.unread_by_user:
        thread.unread_by_user = 0
        thread.save(update_fields=["unread_by_user", "updated_at"])

    return JsonResponse(_serialize_thread(thread, include_messages=True))


@require_POST
def api_v1_support_thread_message(request, thread_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    body, body_error = parse_json_body(request)
    if body_error:
        return body_error
    assert body is not None

    text = (body.get("body") or body.get("message") or "").strip()
    if not text:
        return json_error("body is required", status=400, code="invalid_body")
    if len(text) > MAX_BODY_LEN:
        return json_error("body is too long", status=400, code="invalid_body")

    me = _me(request)
    thread = _get_owned_thread(me, thread_id)
    if isinstance(thread, JsonResponse):
        return thread
    if thread.status == SupportThread.STATUS_CLOSED:
        return json_error("Thread is closed", status=400, code="thread_closed")

    now = timezone.now()
    with transaction.atomic():
        msg = SupportMessage.objects.create(
            thread=thread,
            sender_type=SupportMessage.SENDER_USER,
            sender_user=request.user,
            body=text,
        )
        thread.status = SupportThread.STATUS_WAITING_STAFF
        thread.last_message_at = now
        thread.save(update_fields=["status", "last_message_at", "updated_at"])

    return JsonResponse(_serialize_message(msg), status=201)


@require_POST
def api_v1_support_thread_close(request, thread_id: int):
    err = require_authenticated_json(request)
    if err:
        return err
    me = _me(request)
    thread = _get_owned_thread(me, thread_id)
    if isinstance(thread, JsonResponse):
        return thread

    now = timezone.now()
    with transaction.atomic():
        thread.status = SupportThread.STATUS_CLOSED
        thread.last_message_at = now
        thread.save(update_fields=["status", "last_message_at", "updated_at"])
        SupportMessage.objects.create(
            thread=thread,
            sender_type=SupportMessage.SENDER_SYSTEM,
            body="Обращение закрыто. Вы можете создать новое, если понадобится помощь.",
        )

    thread = SupportThread.objects.prefetch_related("messages").get(pk=thread.pk)
    return JsonResponse(_serialize_thread(thread, include_messages=True))
