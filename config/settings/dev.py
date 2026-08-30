"""Local development. `DJANGO_SETTINGS_MODULE=config.settings.dev`"""

import os

from .base import *  # noqa: F401, F403
from .base import BASE_DIR, IF_TESTING

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key-not-for-any-real-deployment")

DEBUG = True

ALLOWED_HOSTS = ["*"]

ENABLE_API_DOCS = True

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True


# --------------------------------------------------------------
# Database
# --------------------------------------------------------------

if os.getenv("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {"sslmode": os.getenv("DB_SSL_MODE", "allow")},
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:" if IF_TESTING else BASE_DIR / "db.sqlite3",
        },
    }


# --------------------------------------------------------------
# Cache
# --------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "saas-boilerplate-dev",
    },
}


# --------------------------------------------------------------
# Development conveniences
# --------------------------------------------------------------

SESSION_COOKIE_SECURE = False

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

if IF_TESTING:
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": True,
        "handlers": {"null": {"class": "logging.NullHandler"}},
        "root": {"handlers": ["null"]},
    }
