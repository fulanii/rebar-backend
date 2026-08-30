"""
The security posture each environment promises.

Guardrail #10 and docs/configuration.md make specific claims — HTTPS enforced, no
wildcard CORS, the API docs and Django admin confined to development. These assert
them, so loosening one is a failing test rather than a quiet regression.
"""

import importlib
import os
from contextlib import contextmanager
from unittest import mock

import pytest
from django.urls import NoReverseMatch, clear_url_caches, reverse

DEPLOYED_ENV = {
    "SECRET_KEY": "test-key-not-real",
    "DB_NAME": "db",
    "DB_USER": "u",
    "DB_PASSWORD": "p",
    "DB_HOST": "h",
    "REDIS_URL": "redis://localhost:6379/0",
    "ALLOWED_HOSTS": "api.example.com",
    "CORS_ALLOWED_ORIGINS": "https://app.example.com",
}


def load(name):
    """Import a settings module under a stubbed environment."""
    with mock.patch.dict(os.environ, DEPLOYED_ENV, clear=False):
        module = importlib.import_module(f"config.settings.{name}")
        return importlib.reload(module)


@contextmanager
def reloaded_urls():
    """Rebuild the URLconf so a changed setting takes effect, then put it back."""
    import config.urls

    try:
        importlib.reload(config.urls)
        clear_url_caches()
        yield
    finally:
        importlib.reload(config.urls)
        clear_url_caches()


@pytest.fixture(scope="module")
def prod():
    return load("prod")


@pytest.fixture(scope="module")
def staging():
    return load("staging")


class TestProduction:
    def test_debug_is_off(self, prod):
        assert prod.DEBUG is False

    def test_https_is_enforced(self, prod):
        assert prod.SECURE_SSL_REDIRECT is True
        assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")

    def test_hsts_is_set(self, prod):
        assert prod.SECURE_HSTS_SECONDS > 0
        assert prod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True

    def test_cookies_are_secure(self, prod):
        assert prod.SESSION_COOKIE_SECURE is True
        assert prod.CSRF_COOKIE_SECURE is True

    def test_clickjacking_and_sniffing_are_blocked(self, prod):
        assert prod.X_FRAME_OPTIONS == "DENY"
        assert prod.SECURE_CONTENT_TYPE_NOSNIFF is True

    def test_cors_is_not_wildcarded(self, prod):
        assert getattr(prod, "CORS_ALLOW_ALL_ORIGINS", False) is False
        assert prod.CORS_ALLOWED_ORIGINS == ["https://app.example.com"]

    def test_allowed_hosts_is_not_wildcarded(self, prod):
        assert "*" not in prod.ALLOWED_HOSTS
        assert prod.ALLOWED_HOSTS == ["api.example.com"]

    def test_the_fast_test_hasher_is_not_used(self, prod):
        assert "MD5PasswordHasher" not in str(getattr(prod, "PASSWORD_HASHERS", ""))

    def test_it_runs_on_postgres_and_redis(self, prod):
        assert prod.DATABASES["default"]["ENGINE"].endswith("postgresql")
        assert "redis" in prod.CACHES["default"]["BACKEND"].lower()


class TestStaging:
    def test_debug_is_off(self, staging):
        assert staging.DEBUG is False

    def test_cookies_are_secure(self, staging):
        assert staging.SESSION_COOKIE_SECURE is True
        assert staging.CSRF_COOKIE_SECURE is True

    def test_cors_is_not_wildcarded(self, staging):
        assert getattr(staging, "CORS_ALLOW_ALL_ORIGINS", False) is False


class TestApiDocsExposure:
    """
    Publishing the full API surface, and a login form, is avoidable. `ENABLE_API_DOCS`
    is off in `base.py` and turned on only by `dev.py`, so a new environment is closed
    unless it opts in.
    """

    def test_only_development_enables_them(self, prod, staging):
        assert getattr(prod, "ENABLE_API_DOCS", False) is False
        assert getattr(staging, "ENABLE_API_DOCS", False) is False

    def test_the_default_is_off(self):
        from config.settings import base

        assert base.ENABLE_API_DOCS is False

    def test_docs_and_admin_are_mounted_when_enabled(self, settings):
        settings.ENABLE_API_DOCS = True
        with reloaded_urls():
            assert reverse("docs")
            assert reverse("schema")
            assert reverse("admin:index")

    def test_nothing_is_mounted_when_disabled(self, settings):
        settings.ENABLE_API_DOCS = False
        with reloaded_urls():
            for name in ("docs", "schema", "admin:index"):
                with pytest.raises(NoReverseMatch):
                    reverse(name)

    def test_the_api_itself_is_unaffected(self, settings):
        settings.ENABLE_API_DOCS = False
        with reloaded_urls():
            assert reverse("login")
            assert reverse("token_refresh")
