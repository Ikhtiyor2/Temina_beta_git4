# main/ai_workout_plan.py
# Генерация плана тренировок по профилю пользователя (ИИ или правило-бэкофф).

import json
import os
import re
from typing import Any

from django.conf import settings

# Упражнения, доступные в приложении (с URL для старта)
EXERCISE_MAP = {
    "pushups": {"name_ru": "Отжимания", "name_en": "Push-ups", "url": "/train/pushups/", "muscles": ["chest", "arms", "shoulders"]},
    "squats": {"name_ru": "Приседания", "name_en": "Squats", "url": "/train/squats/", "muscles": ["legs", "full_body"]},
    "crunches": {"name_ru": "Скручивания", "name_en": "Crunches", "url": "/train/crunches/", "muscles": ["abs", "core"]},
    "planks": {"name_ru": "Планка", "name_en": "Plank", "url": "/train/planks/", "muscles": ["abs", "core", "shoulders"]},
}


def _profile_to_context(profile) -> str:
    """Собирает текстовое описание профиля для промпта."""
    parts = []
    if profile.age:
        parts.append(f"Age: {profile.age}")
    if profile.height_cm:
        parts.append(f"Height: {profile.height_cm} cm")
    if profile.weight_kg:
        parts.append(f"Weight: {profile.weight_kg} kg")
    if profile.target_weight_kg:
        parts.append(f"Target weight: {profile.target_weight_kg} kg")
    if profile.goals:
        parts.append(f"Goals: {', '.join(profile.goals)}")
    if profile.muscle_focus:
        parts.append(f"Muscle focus: {', '.join(profile.muscle_focus)}")
    if profile.health_limits:
        parts.append(f"Health limitations (avoid or modify): {', '.join(profile.health_limits)}")
    if profile.equipment:
        parts.append(f"Equipment: {', '.join(profile.equipment)}")
    if profile.fitness_level:
        parts.append(f"Fitness level: {profile.fitness_level}")
    if profile.activity_level:
        parts.append(f"Activity level: {profile.activity_level}")
    if profile.workouts_per_week:
        parts.append(f"Workouts per week: {profile.workouts_per_week}")
    if profile.motivation:
        parts.append(f"Motivation: {', '.join(profile.motivation)}")
    if profile.notes:
        parts.append(f"Additional notes: {profile.notes}")
    return "\n".join(parts) if parts else "No details provided."


def _build_fallback_plan(profile) -> list[dict]:
    """План без ИИ: по уровню и ограничениям здоровья выбираем упражнения и объём."""
    level = (profile.fitness_level or "beginner").lower()
    health = set((profile.health_limits or []))
    focus = set((profile.muscle_focus or []))

    # Исключаем по здоровью
    skip = set()
    if "knee" in str(health).lower():
        skip.add("squats")
    if "back" in str(health).lower():
        skip.add("crunches")
        skip.add("pushups")
    if "shoulders" in str(health).lower():
        skip.add("pushups")
    if "hip_joints" in str(health).lower() or "hip" in str(health).lower():
        skip.add("squats")

    rep_ranges = {"beginner": (6, 12), "intermediate": (10, 18), "advanced": (14, 25)}
    min_rep, max_rep = rep_ranges.get(level, (8, 15))
    sets = 2 if level == "beginner" else 3

    plan = []
    for eid, info in EXERCISE_MAP.items():
        if eid in skip:
            continue
        plan.append({
            "id": eid,
            "name": info["name_ru"],
            "name_en": info["name_en"],
            "url": info["url"],
            "sets": sets,
            "reps": f"{min_rep}–{max_rep}",
        })
    return plan


def _call_llm(profile) -> list[dict] | None:
    """
    Генерация плана через LLM: приоритет Groq (GROQ_API_KEY), иначе OpenAI (OPENAI_API_KEY).
    Возвращает список упражнений или None.
    """
    try:
        import openai
    except ImportError:
        return None

    groq_key = getattr(settings, "GROQ_API_KEY", None) or os.environ.get("GROQ_API_KEY")
    openai_key = getattr(settings, "OPENAI_API_KEY", None) or os.environ.get("OPENAI_API_KEY")

    if groq_key:
        api_key = groq_key
        base_url = "https://api.groq.com/openai/v1"
        model = getattr(settings, "GROQ_MODEL", None) or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
    elif openai_key:
        api_key = openai_key
        base_url = None
        model = "gpt-4o-mini"
    else:
        return None

    context = _profile_to_context(profile)
    system = """You are a fitness coach for TeminaFit. The app only has these exercises: pushups, squats, crunches, planks.
Return a JSON array of today's workout. Each item: {"id": "pushups"|"squats"|"crunches"|"planks", "sets": number, "reps": "e.g. 10-15" or for planks "reps": "30-60 sec"}.
Respect user's health limitations (avoid or suggest fewer reps). Keep 3-4 exercises, 2-4 sets each. Reply with ONLY the JSON array, no markdown."""

    user_msg = f"User profile:\n{context}\n\nGenerate today's workout as a JSON array of exercises (id, sets, reps)."

    try:
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = openai.OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        arr = json.loads(text)
        out = []
        for item in arr:
            eid = (item.get("id") or "").lower().replace("-", "").replace(" ", "")
            if eid == "plank":
                eid = "planks"
            if eid not in EXERCISE_MAP:
                continue
            info = EXERCISE_MAP[eid]
            out.append({
                "id": eid,
                "name": info["name_ru"],
                "name_en": info["name_en"],
                "url": info["url"],
                "sets": int(item.get("sets", 3)),
                "reps": str(item.get("reps", "10-15")),
            })
        return out if out else None
    except Exception:
        return None


def generate_workout_plan(profile) -> tuple[list[dict], bool]:
    """
    Генерирует план тренировки по профилю.
    Сначала пробует Groq или OpenAI; при отсутствии ключей или ошибке — правило-бэкофф.
    Возвращает (plan, is_ai: True если план от ИИ).
    """
    plan = _call_llm(profile)
    if plan:
        return plan, True
    return _build_fallback_plan(profile), False
