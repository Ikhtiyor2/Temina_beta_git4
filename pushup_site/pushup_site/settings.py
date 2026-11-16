from pathlib import Path
import os
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
#obnova1
#obnova22У

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# В продакшене обязательно задать DJANGO_SECRET_KEY в .env или окружении сервера.
_secret = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not _secret:
    if os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes'):
        _secret = 'django-insecure-dev-only-do-not-deploy'
    else:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false')
SECRET_KEY = _secret

DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

_env_hosts = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]
if _env_hosts:
    ALLOWED_HOSTS = _env_hosts
elif DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '10.0.2.2']
else:
    ALLOWED_HOSTS = [
        'temina.fit',
        'www.temina.fit',
        '138.249.7.37',
        '127.0.0.1',
        'localhost',
    ]

# --- Установленные приложения ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',  # твое приложение
]

# --- Middleware ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- URL конфигурация ---
ROOT_URLCONF = 'pushup_site.urls'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

# --- Настройки шаблонов ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # общая папка шаблонов
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'main.context_processors.language',
            ],
        },
    },
]

# --- WSGI ---
WSGI_APPLICATION = 'pushup_site.wsgi.application'

# --- База данных ---
# Все параметры берутся из окружения (.env); значения по умолчанию — локальный Postgres.
# Экстренный откат на SQLite: DB_ENGINE=sqlite в .env.
if os.environ.get('DB_ENGINE', 'postgres').strip().lower() in ('sqlite', 'sqlite3'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'temina'),
            'USER': os.environ.get('DB_USER', 'temina'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'temina'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        }
    }



# ... остальные настройки

# --- Пароли ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Локализация ---
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

# --- Статические файлы ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- Медиа (если потом захочешь сохранять видео/фото) ---
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Default primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- HTTPS / cookies ---
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # JS читает csrftoken для X-CSRFToken
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', '1').lower() in ('1', 'true', 'yes')
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_REFERRER_POLICY = 'same-origin'

CSRF_TRUSTED_ORIGINS = [
    "https://temina.fit",
    "https://www.temina.fit",
]
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://45.138.158.58",
        "http://temina.fit",
        "http://www.temina.fit",
    ])

# --- Подписки (RevenueCat) ---
# Секрет, который ты задаёшь в дашборде RevenueCat (Integrations → Webhooks →
# Authorization header) и который RevenueCat шлёт в заголовке Authorization каждого вебхука.
REVENUECAT_WEBHOOK_AUTH = os.environ.get("REVENUECAT_WEBHOOK_AUTH", "")
# Secret API key (v1) из RevenueCat для серверной сверки статуса через REST.
REVENUECAT_SECRET_API_KEY = os.environ.get("REVENUECAT_SECRET_API_KEY", "")
# Идентификатор entitlement, который считаем «премиумом».
REVENUECAT_PRO_ENTITLEMENT = os.environ.get("REVENUECAT_PRO_ENTITLEMENT", "pro")

# --- Email (soft verification) ---
# Если задан EMAIL_HOST_PASSWORD (Resend API key) — шлём через SMTP,
# даже при DEBUG. Иначе в DEBUG письма идут в консоль.
_email_backend = os.environ.get("EMAIL_BACKEND", "").strip()
_email_password = os.environ.get("EMAIL_HOST_PASSWORD", "").strip()
_email_host = os.environ.get("EMAIL_HOST", "").strip()
if _email_backend:
    EMAIL_BACKEND = _email_backend
elif _email_host and _email_password:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
elif DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = _email_host or "smtp.resend.com"
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "resend").strip() or "resend"
EMAIL_HOST_PASSWORD = _email_password
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1").lower() in ("1", "true", "yes")
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "0").lower() in ("1", "true", "yes")
# From должен быть на верифицированном домене Resend (сейчас: noreply.temina.fit).
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "Temina <hello@noreply.temina.fit>",
).strip()
# Базовый URL для ссылок в письмах (без завершающего /).
PUBLIC_BASE_URL = os.environ.get(
    "PUBLIC_BASE_URL",
    "http://127.0.0.1:8000" if DEBUG else "https://temina.fit",
).strip().rstrip("/")

# --- AI для плана тренировок (OpenAI или Groq) ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"

# Токен бота из BotFather. Нужен, чтобы проверять подпись Mini App. В репозиторий не класть.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

# Cloudflare Turnstile на форме регистрации (тихий режим, без галочек).
# Виджет: dash.cloudflare.com → Turnstile → домен temina.fit, режим Managed.
TURNSTILE_SITE_KEY = os.environ.get("TURNSTILE_SITE_KEY", "").strip()
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "").strip()
