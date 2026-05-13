import os
from pathlib import Path
from dotenv import load_dotenv

# Load shared .env from python/ directory, then local .env as override
_python_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_python_dir / ".env")
load_dotenv(override=False)  # local .env if exists

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-key-change-in-production-abcdef123456")

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
# Leading-dot entries match any subdomain (ngrok preview URLs).
if DEBUG:
    for _ng in (".ngrok-free.app", ".ngrok.io", ".ngrok.app"):
        if _ng not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_ng)

# -- Backend API URL (the FastAPI backend) --
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8040")

# ngrok / reverse proxy: trust X-Forwarded-Proto and Host so request.is_secure() and CSRF match HTTPS.
_trust_proxy = os.getenv("DJANGO_TRUST_PROXY_HEADERS", "true" if DEBUG else "false").lower() in (
    "true",
    "1",
    "yes",
)
if _trust_proxy:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

# CSRF for HTMX POSTs; "*" in netloc allows any subdomain (Django 4+).
_csrf_env = os.getenv("CSRF_TRUSTED_ORIGINS", "").strip()
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_env.split(",") if o.strip()]
if DEBUG and os.getenv("CSRF_TRUST_NGROK", "true").lower() in ("true", "1", "yes"):
    _csrf_ngrok_defaults = (
        "http://localhost:8050",
        "http://127.0.0.1:8050",
        "https://*.ngrok-free.app",
        "http://*.ngrok-free.app",
        "https://*.ngrok.io",
        "http://*.ngrok.io",
        "https://*.ngrok.app",
        "http://*.ngrok.app",
    )
    for _o in _csrf_ngrok_defaults:
        if _o not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_o)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "core.middleware.TenantMiddleware",
]

ROOT_URLCONF = "voiceflow.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.global_context",
            ],
        },
    },
]

WSGI_APPLICATION = "voiceflow.wsgi.application"


def _db_tcp_host() -> str:
    """Use IPv4 loopback for Docker-mapped Postgres on Windows (localhost -> ::1 often breaks)."""
    h = (os.getenv("DB_HOST") or "127.0.0.1").strip()
    if h.lower() in ("localhost", "::1"):
        return "127.0.0.1"
    return h


# Database — shared Postgres with the FastAPI backend
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "voiceflow_prod"),
        "USER": os.getenv("DB_USER", "vf_admin"),
        "PASSWORD": os.getenv("DB_PASSWORD", "vf_secure_2025!"),
        "HOST": _db_tcp_host(),
        "PORT": os.getenv("DB_PORT", "8010"),
    }
}

AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # HTMX needs to read CSRF token
