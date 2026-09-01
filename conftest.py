"""Fixtures available to every test. See docs/ai/conventions.md."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

User = get_user_model()


class OutboundEmail:
    """
    Handle on both email providers' network calls, with either standing in for "an
    email was attempted" so tests do not care which provider is configured.
    """

    def __init__(self, resend_send, brevo_client):
        self.resend = resend_send
        self.brevo = brevo_client

    @property
    def brevo_send(self):
        return self.brevo.return_value.transactional_emails.send_transac_email

    @property
    def called(self):
        return self.resend.called or self.brevo.called

    def reset_mock(self):
        self.resend.reset_mock()
        self.brevo.reset_mock()


@pytest.fixture(autouse=True)
def block_outbound_email():
    """Makes it impossible for the suite to send a real email. Yields both mocks."""
    with patch("resend.Emails.send") as resend_send, patch("brevo.Brevo") as brevo_client:
        yield OutboundEmail(resend_send, brevo_client)


@pytest.fixture(autouse=True)
def email_configured(settings):
    """
    Give every test a working email configuration.

    There is no fallback body, so without an API key and template ids `_send` returns
    early and nothing reaches a provider, which would make "an email was sent"
    unassertable everywhere. The provider calls themselves are still mocked by
    `block_outbound_email`; tests covering the unconfigured cases override these.
    """
    settings.EMAIL_PROVIDER = "brevo"
    settings.BREVO_API_KEY = "test-brevo-key"
    settings.RESEND_API_KEY = "test-resend-key"
    settings.VERIFICATION_TEMPLATE_ID = "1"
    settings.PASSWORD_RESET_TEMPLATE_ID = "2"
    settings.PASSWORD_CHANGED_TEMPLATE_ID = "3"
    settings.EMAIL_CHANGE_TEMPLATE_ID = "4"


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """
    Resets rate-limit counters between tests.

    Load-bearing: the in-memory database restarts row ids at 1 for every test, so all
    tests share one per-user throttle key. Without this the counter accumulates and
    unrelated tests start failing with 429.
    """
    yield
    cache.clear()


@pytest.fixture
def user_password():
    return "SecurePass123!"


@pytest.fixture
def base_user(db, user_password):
    """A verified, active user."""
    return User.objects.create_user(
        email="user@example.com",
        password=user_password,
        first_name="Test",
        last_name="User",
        phone_number="5551234567",
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def second_user(db, user_password):
    """A second account, for per-user isolation tests."""
    return User.objects.create_user(
        email="other@example.com",
        password=user_password,
        first_name="Other",
        last_name="User",
        phone_number="5559876543",
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def unverified_user(db, user_password):
    """A registered account that has not yet entered its emailed code."""
    return User.objects.create_user(
        email="pending@example.com",
        password=user_password,
        first_name="Pending",
        last_name="User",
        phone_number="5555550100",
        is_active=False,
        is_verified=False,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, base_user):
    """
    A client authenticated as `base_user`.

    Skips token validation, so tests *about* authentication must send a real token.
    """
    api_client.force_authenticate(user=base_user)
    return api_client


@pytest.fixture
def unlimited_requests(monkeypatch, settings):
    """
    Raise every rate limit out of the way for one test.

    Only for tests of a control that sits *behind* the throttle, the per-code attempt
    counter, say, which needs more requests than one IP is ever allowed. The real rates
    stay where they are; `tests/views/test_throttling.py` pins them.

    `SimpleRateThrottle` reads the rates once at import, so overriding the setting is
    not enough, the class attribute is what every throttle actually consults.
    """
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {scope: "1000/hour" for scope in rates})
