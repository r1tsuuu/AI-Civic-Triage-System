"""
Development settings.
Reads all sensitive values from a .env file via python-decouple.
Never commit .env to git.
"""
from decouple import config, Csv

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY", default="dev-insecure-change-before-production")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,testserver", cast=Csv())

# ---------------------------------------------------------------------------
# Database  (PostgreSQL; fall back to SQLite if DATABASE_URL is unset locally)
# ---------------------------------------------------------------------------
import dj_database_url  # noqa: E402 — imported here to keep base.py clean

_database_url = config("DATABASE_URL", default=None)

if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Local SQLite fallback — acceptable for Day 1 if Postgres isn't up yet
    import os  # noqa: E402
    from pathlib import Path  # noqa: E402

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path(__file__).resolve().parent.parent.parent / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Meta / Facebook
# ---------------------------------------------------------------------------
META_APP_ID = config("META_APP_ID", default="")
META_APP_SECRET = config("META_APP_SECRET", default="")
META_VERIFY_TOKEN = config("META_VERIFY_TOKEN", default="")
META_PAGE_ACCESS_TOKEN = config("META_PAGE_ACCESS_TOKEN", default="")

# ---------------------------------------------------------------------------
# NLP
# ---------------------------------------------------------------------------
NLP_MODEL_PATH = config("NLP_MODEL_PATH", default="ml/models/classifier.pkl")
NER_MODEL_PATH = config("NER_MODEL_PATH", default="ml/models/ner_model")
NLP_CONFIDENCE_THRESHOLD = config("NLP_CONFIDENCE_THRESHOLD", default=0.65, cast=float)

# ---------------------------------------------------------------------------
# Dashboard password gate (TASK-001)
# ---------------------------------------------------------------------------
DEMO_PASSWORD = config("DEMO_PASSWORD", default="actsDemo2025")

# ---------------------------------------------------------------------------
# Development-only conveniences
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
