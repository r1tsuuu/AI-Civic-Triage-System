"""
Production settings.
All values MUST come from environment variables — no defaults with real data.
"""
from decouple import config, Csv
import dj_database_url

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Core security
# ---------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")  # No default — crash if missing
DEBUG = False
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*", cast=Csv())

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------------------------
# HTTPS / cookie security
# ---------------------------------------------------------------------------
# Railway / Render terminate TLS at the load balancer and forward plain HTTP.
# Without this, SECURE_SSL_REDIRECT causes an infinite redirect loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_REDIRECT_EXEMPT = [
    r'^health/',  
    r'health',  
]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Static files — served by WhiteNoise (no separate static server needed)
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # immediately after SecurityMiddleware
] + [m for m in __import__('config.settings.base', fromlist=['MIDDLEWARE']).MIDDLEWARE
     if m not in (
         "django.middleware.security.SecurityMiddleware",
     )]

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# ---------------------------------------------------------------------------
# Meta / Facebook
# ---------------------------------------------------------------------------
META_APP_ID = config("META_APP_ID")
META_APP_SECRET = config("META_APP_SECRET")
META_VERIFY_TOKEN = config("META_VERIFY_TOKEN")
META_PAGE_ACCESS_TOKEN = config("META_PAGE_ACCESS_TOKEN")

# ---------------------------------------------------------------------------
# NLP
# ---------------------------------------------------------------------------
NLP_MODEL_PATH = config("NLP_MODEL_PATH", default="ml/models/classifier_v2.pkl")
NER_MODEL_PATH = config("NER_MODEL_PATH", default="ml/models/ner_model_v1")
NLP_CONFIDENCE_THRESHOLD = config("NLP_CONFIDENCE_THRESHOLD", cast=float, default=0.65)

# ---------------------------------------------------------------------------
# Dashboard password gate (TASK-001)
# ---------------------------------------------------------------------------
DEMO_PASSWORD = config("DEMO_PASSWORD")

# ---------------------------------------------------------------------------
# Logging — emit to stdout so Railway/Render captures it
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
