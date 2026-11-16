# main/workout_builder.py
# Логика ИИ-помощника: опрос (настроение, травмы, уставшие мышцы) и генерация плана тренировки.

from typing import Any

# Доступные упражнения (без подтягиваний)
EXERCISES = {
    "pushups": {"name": "Отжимания", "muscles": ["грудь", "трицепсы", "плечи"], "url": "/train/pushups/"},
    "squats": {"name": "Приседания", "muscles": ["ноги", "ягодицы", "колени"], "url": "/train/squats/"},
    "crunches": {"name": "Скручивания", "muscles": ["пресс", "кор"], "url": "/train/crunches/"},
    "planks": {"name": "Планка", "muscles": ["пресс", "кор", "плечи"], "url": "/train/planks/"},
}

# Шаги диалога
STEP_MOOD = "mood"
STEP_INJURIES = "injuries"
STEP_SORE = "sore"
STEP_DONE = "done"

INITIAL_STATE = {"step": STEP_MOOD, "mood": None, "injuries": [], "sore": []}


def get_next_question(state: dict) -> dict:
    """Возвращает следующий вопрос ассистента и варианты ответа (если есть)."""
    step = state.get("step", STEP_MOOD)

    if step == STEP_MOOD:
        return {
            "message": "Как ты себя чувствуешь сегодня? От этого зависит интенсивность тренировки.",
            "options": [
                {"value": "high", "label": "Полон сил, готов к нагрузке"},
                {"value": "medium", "label": "Нормально, средняя нагрузка"},
                {"value": "low", "label": "Устал, хочу лёгкую тренировку"},
            ],
            "step": STEP_MOOD,
        }
    if step == STEP_INJURIES:
        return {
            "message": "Есть ли травмы или боль, которые нужно учесть? Выбери зоны, которые нужно избегать.",
            "options": [
                {"value": "none", "label": "Нет травм"},
                {"value": "knees", "label": "Колени"},
                {"value": "wrists", "label": "Запястья / руки"},
                {"value": "back", "label": "Спина"},
                {"value": "shoulders", "label": "Плечи"},
            ],
            "step": STEP_INJURIES,
        }
    if step == STEP_SORE:
        return {
            "message": "Какие мышцы ещё не восстановились или болят после прошлой тренировки? Их не будем нагружать.",
            "options": [
                {"value": "none", "label": "Всё в порядке"},
                {"value": "chest", "label": "Грудь / трицепсы"},
                {"value": "legs", "label": "Ноги / ягодицы"},
                {"value": "core", "label": "Пресс / кор"},
            ],
            "step": STEP_SORE,
        }
    return {"message": "", "options": [], "step": step}


def apply_answer(state: dict, step: str, value: Any) -> dict:
    """Обновляет state по ответу пользователя. value — строка или список (для травм/уставших мышц)."""
    state = dict(state)
    if step == STEP_MOOD:
        state["mood"] = value if isinstance(value, str) else (value[0] if value else "medium")
        state["step"] = STEP_INJURIES
    elif step == STEP_INJURIES:
        if isinstance(value, list):
            state["injuries"] = [v for v in value if v != "none"]
        else:
            state["injuries"] = [] if value == "none" else [value]
        state["step"] = STEP_SORE
    elif step == STEP_SORE:
        if isinstance(value, list):
            state["sore"] = [v for v in value if v != "none"]
        else:
            state["sore"] = [] if value == "none" else [value]
        state["step"] = STEP_DONE
    return state


def build_plan(state: dict) -> list[dict]:
    """Строит план тренировки: список упражнений с учётом настроения, травм и уставших мышц."""
    mood = state.get("mood") or "medium"
    injuries = state.get("injuries") or []
    sore = state.get("sore") or []

    # Исключаем упражнения по травмам
    skip = set()
    if "knees" in injuries or "legs" in injuries:
        skip.add("squats")
    if "wrists" in injuries or "shoulders" in injuries:
        skip.add("pushups")
    if "back" in injuries:
        skip.add("crunches")
        skip.add("pushups")  # при болях в спине отжимания тоже осторожнее

    # Исключаем по уставшим мышцам
    if "chest" in sore:
        skip.add("pushups")
    if "legs" in sore:
        skip.add("squats")
    if "core" in sore:
        skip.add("crunches")

    # Интенсивность по настроению
    rep_ranges = {"high": (12, 20), "medium": (8, 15), "low": (5, 10)}
    min_rep, max_rep = rep_ranges.get(mood, (8, 15))

    plan = []
    for eid, info in EXERCISES.items():
        if eid in skip:
            continue
        plan.append({
            "id": eid,
            "name": info["name"],
            "url": info["url"],
            "reps": f"{min_rep}–{max_rep}",
            "sets": 2 if mood == "low" else 3,
        })
    return plan


def get_ai_reply(state: dict, user_message: str = "", option_value: Any = None) -> tuple[dict, dict]:
    """
    Обрабатывает ответ пользователя (текст или выбор option) и возвращает (new_state, reply).
    reply: { "message": str, "plan": list | None, "options": list }
    option_value: строка или список (для множественного выбора травм/соре)
    """
    step = state.get("step", STEP_MOOD)

    # Если пользователь выбрал вариант из options
    if option_value is not None and option_value != "":
        state = apply_answer(state, step, option_value)
        step = state["step"]

    if step != STEP_DONE:
        next_q = get_next_question(state)
        return state, {"message": next_q["message"], "plan": None, "options": next_q.get("options", [])}

    # Генерируем план
    plan = build_plan(state)
    mood_text = {"high": "высокой", "medium": "средней", "low": "лёгкой"}.get(state.get("mood"), "средней")
    msg = f"Вот твоя персональная тренировка {mood_text} интенсивности. "
    if state.get("injuries") or state.get("sore"):
        msg += "Учтены травмы и уставшие мышцы. "
    msg += "Можешь начать с первого упражнения по кнопке ниже."
    return state, {"message": msg, "plan": plan, "options": []}
