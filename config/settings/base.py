"""Settings shared by every environment. See docs/configuration.md."""

import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IF_TESTING = "test" in sys.argv or "pytest" in sys.modules or os.getenv("CI") == "true"

load_dotenv()


# --------------------------------------------------------------
# Applications
# --------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    # Local
    "authentication",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "config.middleware.RequestLoggingMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"


# --------------------------------------------------------------
# Auth
# --------------------------------------------------------------

AUTH_USER_MODEL = "authentication.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# --------------------------------------------------------------
# Static files
# --------------------------------------------------------------

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------

REST_FRAMEWORK = {
    "NUM_PROXIES": 1,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": ("authentication.auth.SuspensionAwareJWTAuthentication",),
    "DEFAULT_THROTTLE_RATES": {
        "registration": "5/hour",
        "login": "20/hour",
        "token_refresh": "30/minute",
        "google_auth": "20/hour",
        "google_callback": "20/hour",
        "code_request": "5/hour",
        "code_submit": "5/hour",
        "password_reset": "5/hour",
        "profile_update": "20/hour",
        "email_change": "5/hour",
        "account_deletion": "5/hour",
        "user_info": "60/minute",
    },
}


# --------------------------------------------------------------
# JWT
# --------------------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
    "BLACKLIST_AFTER_ROTATION": True,
}


# --------------------------------------------------------------
# Background jobs (Celery)
# --------------------------------------------------------------

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "")

CELERY_TASK_ALWAYS_EAGER = IF_TESTING or not CELERY_BROKER_URL

CELERY_TASK_EAGER_PROPAGATES = False

CELERY_TASK_SERIALIZER = "json"

CELERY_ACCEPT_CONTENT = ["json"]

CELERY_RESULT_BACKEND = None

CELERY_TIMEZONE = TIME_ZONE

CELERY_TASK_TIME_LIMIT = 120

CELERY_TASK_SOFT_TIME_LIMIT = 60

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_WORKER_SEND_TASK_EVENTS = False

EMAIL_MAX_RETRIES = 0 if IF_TESTING else 3


# --------------------------------------------------------------
# API documentation (drf-spectacular)
# --------------------------------------------------------------

ENABLE_API_DOCS = False

SPECTACULAR_SETTINGS = {
    "TITLE": "Rebar API",
    "DESCRIPTION": (
        "Django REST Framework backend with email-first JWT authentication, "
        "6-digit email verification, password reset, and Google OAuth."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}


# --------------------------------------------------------------
# Third-party keys
# --------------------------------------------------------------

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "brevo")

BREVO_API_KEY = os.getenv("BREVO_API_KEY")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

VERIFICATION_TEMPLATE_ID = os.getenv("VERIFICATION_TEMPLATE_ID", "")

PASSWORD_RESET_TEMPLATE_ID = os.getenv("PASSWORD_RESET_TEMPLATE_ID", "")

PASSWORD_CHANGED_TEMPLATE_ID = os.getenv("PASSWORD_CHANGED_TEMPLATE_ID", "")

EMAIL_CHANGE_TEMPLATE_ID = os.getenv("EMAIL_CHANGE_TEMPLATE_ID", "")

DOMAIN = os.getenv("DOMAIN", "localhost")


# --------------------------------------------------------------
# Logging
# --------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {
            "()": "config.middleware.ColoredFormatter",
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "app": {
            "()": "config.middleware.ColoredFormatter",
            "format": "[{levelname}] {asctime} \033[96m[app]\033[0m {name}: {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        "console_app": {"class": "logging.StreamHandler", "formatter": "app"},
    },
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "config.middleware": {"handlers": ["console_app"], "level": "INFO", "propagate": False},
        "authentication": {"handlers": ["console_app"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}
