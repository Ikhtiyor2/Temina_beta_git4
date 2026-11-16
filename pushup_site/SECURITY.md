# Безопасность TeminaFit

Актуальный статус мер безопасности в коде (после hardening `settings.py`).

## Что исправлено в коде

### 1. Настройки Django (`pushup_site/settings.py`)

- **SECRET_KEY** — из `DJANGO_SECRET_KEY` (`.env` / окружение сервера).
- **DEBUG** — из `DJANGO_DEBUG` (по умолчанию `False`).
- **ALLOWED_HOSTS** — из `ALLOWED_HOSTS` или продакшен-список; при DEBUG — localhost.
- **AUTH_PASSWORD_VALIDATORS** — минимум 8 символов, типичные/числовые пароли отклоняются.
- **Cookies**: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` при `DEBUG=False`; `HttpOnly` для сессии; `SameSite=Lax`.
- **CSRF_TRUSTED_ORIGINS** — HTTPS для `temina.fit`; HTTP только при `DEBUG=True`.

### 2. API анкеты (assessment)

- `POST /api/v1/users/me/assessment/dev/` доступен **только при `DEBUG=True`**. На проде — 404.

### 3. Игровая валюта

- `POST /api/player/add-currency/` — **только `is_staff`**. Обычные пользователи не могут накручивать валюту.

### 4. Rate limiting (auth)

- Логин: не более **10** попыток в минуту с IP.
- Регистрация: не более **5** в минуту с IP.
- Реализация: `main/rate_limit.py` + Django cache.

### 5. Секреты в репозитории

- `.gitignore`: `local.properties`, `*.jks`, `klyuch2`, `db.sqlite3`.
- Шаблон: `temina-android/local.properties.example`.
- Токены убраны из `.cursor/rules/`.

## Обязательно на сервере (ручные шаги)

1. **Ротировать** все ранее утёкшие секреты: GitHub token, Maps API key, keystore passwords, `DJANGO_SECRET_KEY`.
2. Задать в `.env` на сервере:
   ```bash
   DJANGO_SECRET_KEY=<случайная строка 50+ символов>
   DJANGO_DEBUG=0
   ```
3. Не задавать `ENABLE_DEMO_LOGIN` на проде.
4. Убрать из истории git (если ещё не сделано): `db.sqlite3`, `local.properties`, keystore — через `git filter-repo` или BFG.

## Рекомендации (следующий этап)

- PostgreSQL вместо SQLite на проде.
- Rate limit на AI-эндпоинты (`process_ai_frame`).
- XSS-аудит шаблонов с `innerHTML`.
- JWT или token auth для Android вместо session + `csrf_exempt`.
- `pip audit` / обновление зависимостей.
- Настроить SMTP (`EMAIL_*` в `.env`) для доставки писем soft email verification
  (сейчас при DEBUG письма идут в консоль).

## Soft email verification

- После регистрации отправляется ссылка `/verify-email/<token>/` (48ч).
- API: `POST /api/auth/resend-verification/`, `GET|POST /api/auth/verify-email/`.
- Вход и использование приложения **не блокируются** до подтверждения (`Player.email_verified`).
- В `/api/auth/me/` поле `emailVerified`.

## Кратко

| Риск | Статус |
|------|--------|
| Утечка секретов в git | Частично: gitignore + шаблоны; нужна ротация ключей |
| Слабые пароли | Исправлено (валидаторы) |
| Dev assessment на проде | Закрыто |
| Накрутка валюты | Закрыто (staff-only) |
| Брутфорс логина | Смягчено (rate limit) |
| CSRF на mobile API | Осознанный компромисс; HTTPS обязателен |
