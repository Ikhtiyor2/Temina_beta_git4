"""API: правила формы для AI-тренировок (гантели и др.)."""
import json
import logging
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_RULES_BY_LOCALE = {
    "ru": _DATA_DIR / "form_rules_dumbbell_v1.json",
    "en": _DATA_DIR / "form_rules_dumbbell_v1_en.json",
    "uz": _DATA_DIR / "form_rules_dumbbell_v1_uz.json",
}
_DEFAULT_RULES_PATH = _RULES_BY_LOCALE["ru"]


def _resolve_rules_path(locale: str) -> Path:
    key = (locale or "ru").strip().lower()[:2]
    path = _RULES_BY_LOCALE.get(key)
    if path is not None and path.is_file():
        return path
    return _DEFAULT_RULES_PATH


@require_GET
def api_v1_form_rules(request):
    """
    GET /api/v1/form-rules/?exercise_group=DUMBBELL&locale=ru|en|uz
    Отдаёт JSON правил (та же схема, что в Android assets).
    """
    group = (request.GET.get("exercise_group") or "DUMBBELL").strip().upper()
    if group != "DUMBBELL":
        return JsonResponse(
            {"success": False, "error": "unsupported_group", "message": "Only DUMBBELL rules in v1"},
            status=400,
        )
    locale = (request.GET.get("locale") or "ru").strip().lower()
    rules_path = _resolve_rules_path(locale)
    try:
        raw = rules_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as e:
        logger.exception("form_rules read failed locale=%s path=%s", locale, rules_path)
        return JsonResponse(
            {"success": False, "error": "rules_unavailable", "message": str(e)},
            status=500,
        )
    response = JsonResponse(data)
    response["Cache-Control"] = "public, max-age=3600"
    return response
