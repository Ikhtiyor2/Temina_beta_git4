"""Localized quest titles/descriptions by quest_type + daily/weekly flag."""

from __future__ import annotations

from typing import Any

from main.locale_content import normalize_lang

# (daily_title, weekly_title, daily_desc_tpl, weekly_desc_tpl)
# Templates may include {goal}. Weekly title/desc used when is_daily=False.
_QUEST_COPY: dict[str, dict[str, tuple[str, str, str, str]]] = {
    "PUSHUP": {
        "ru": (
            "💪 Сила отжиманий",
            "🏆 Недельная сила",
            "Выполни {goal} классических отжиманий",
            "Сделай {goal} отжиманий за неделю",
        ),
        "en": (
            "💪 Push-up power",
            "🏆 Weekly strength",
            "Do {goal} classic push-ups",
            "Do {goal} push-ups this week",
        ),
        "uz": (
            "💪 Push-up kuchi",
            "🏆 Haftalik kuch",
            "{goal} ta klassik push-up bajaring",
            "Bir haftada {goal} ta push-up bajaring",
        ),
    },
    "SQUAT": {
        "ru": (
            "🦵 Выносливость ног",
            "🦵 Недельная выносливость",
            "Выполни {goal} классических приседаний",
            "Выполни {goal} приседаний за неделю",
        ),
        "en": (
            "🦵 Leg endurance",
            "🦵 Weekly endurance",
            "Do {goal} classic squats",
            "Do {goal} squats this week",
        ),
        "uz": (
            "🦵 Oyoq chidamliligi",
            "🦵 Haftalik chidamlilik",
            "{goal} ta klassik squat bajaring",
            "Bir haftada {goal} ta squat bajaring",
        ),
    },
    "PULLUP": {
        "ru": (
            "🎯 Сила хвата",
            "🎯 Недельный хват",
            "Выполни {goal} классических подтягиваний",
            "Сделай {goal} подтягиваний за неделю",
        ),
        "en": (
            "🎯 Grip strength",
            "🎯 Weekly grip",
            "Do {goal} classic pull-ups",
            "Do {goal} pull-ups this week",
        ),
        "uz": (
            "🎯 Ushlash kuchi",
            "🎯 Haftalik ushlash",
            "{goal} ta klassik pull-up bajaring",
            "Bir haftada {goal} ta pull-up bajaring",
        ),
    },
    "CRUNCH": {
        "ru": (
            "🔥 Пресс сталь",
            "🔥 Пресс сталь",
            "Выполни {goal} классических скручиваний",
            "Выполни {goal} классических скручиваний",
        ),
        "en": (
            "🔥 Steel core",
            "🔥 Steel core",
            "Do {goal} classic crunches",
            "Do {goal} classic crunches",
        ),
        "uz": (
            "🔥 Po‘lat press",
            "🔥 Po‘lat press",
            "{goal} ta klassik crunch bajaring",
            "{goal} ta klassik crunch bajaring",
        ),
    },
    "TABATA": {
        "ru": ("⚡ Табата", "⚡ Табата", "Заверши 1 табата-тренировку", "Заверши 1 табата-тренировку"),
        "en": ("⚡ Tabata", "⚡ Tabata", "Finish 1 Tabata workout", "Finish 1 Tabata workout"),
        "uz": ("⚡ Tabata", "⚡ Tabata", "1 ta Tabata mashg‘ulotini yakunlang", "1 ta Tabata mashg‘ulotini yakunlang"),
    },
    "RUN": {
        "ru": ("🏃 Бег", "🏃 Бег", "Пробеги {goal} км", "Пробеги {goal} км"),
        "en": ("🏃 Run", "🏃 Run", "Run {goal} km", "Run {goal} km"),
        "uz": ("🏃 Yugurish", "🏃 Yugurish", "{goal} km yuguring", "{goal} km yuguring"),
    },
    "DAILY_LOGIN": {
        "ru": (
            "📅 Ежедневный вход",
            "📅 Ежедневный вход",
            "Зайди в приложение чтобы получить бонус!",
            "Зайди в приложение чтобы получить бонус!",
        ),
        "en": (
            "📅 Daily check-in",
            "📅 Daily check-in",
            "Open the app to claim your bonus!",
            "Open the app to claim your bonus!",
        ),
        "uz": (
            "📅 Kunlik kirish",
            "📅 Kunlik kirish",
            "Bonus olish uchun ilovaga kiring!",
            "Bonus olish uchun ilovaga kiring!",
        ),
    },
}


def localize_quest_text(quest: Any, lang: str | None = None) -> tuple[str, str]:
    """Return (title, description) for the requested language."""
    key = normalize_lang(lang)
    copy = _QUEST_COPY.get(getattr(quest, "quest_type", "") or "")
    if not copy:
        return getattr(quest, "title", "") or "", getattr(quest, "description", "") or ""
    pack = copy.get(key) or copy["ru"]
    daily_title, weekly_title, daily_desc, weekly_desc = pack
    is_daily = bool(getattr(quest, "is_daily", True))
    title = daily_title if is_daily else weekly_title
    desc_tpl = daily_desc if is_daily else weekly_desc
    goal = int(getattr(quest, "goal", 0) or 0)
    try:
        description = desc_tpl.format(goal=goal)
    except (KeyError, ValueError):
        description = desc_tpl
    return title, description
