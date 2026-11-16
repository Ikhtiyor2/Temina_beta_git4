# main/context_processors.py
def language(request):
    """Добавляет current_lang (ru/en/uz) из cookie для переключения языка в шаблонах."""
    lang = request.COOKIES.get("temina_lang", "ru")
    if lang not in ("ru", "en", "uz"):
        lang = "ru"
    return {"current_lang": lang}
