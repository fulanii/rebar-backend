"""
Rate limits.

Guardrail #2: these are the only thing standing between a public endpoint and someone
guessing 6-digit codes or spraying passwords, so they are tested like any other
security control.

Each test reads its limit from settings and sends one request too many, so raising a
limit does not quietly slip past — it changes how many requests the test sends, while
`TestConfiguredRates` pins the numbers themselves.
"""

import pytest
from django.urls import reverse

from authentication import throttles

pytestmark = pytest.mark.django_db

RATES = {
    "registration": "5/hour",
    "login": "20/hour",
    "token_refresh": "30/minute",
    "google_auth": "20/hour",
    "code_request": "5/hour",
    "code_submit": "5/hour",
    "password_reset": "5/hour",
    "user_info": "60/minute",
}


def limit(settings, scope):
    return int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][scope].split("/")[0])


def exhaust(send, times):
    """Send `times` requests and return the status of one more."""
    for _ in range(times):
        send()
    return send().status_code


class TestConfiguredRates:
    @pytest.mark.parametrize("scope,expected", RATES.items())
    def test_the_documented_rate_is_configured(self, settings, scope, expected):
        assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][scope] == expected

    def test_every_scope_has_a_throttle_class(self, settings):
        declared = set(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])
        ours = [c for c in vars(throttles).values() if isinstance(c, type) and c.__module__ == throttles.__name__]
        used = {c.scope for c in ours}

        assert declared == used, "a rate without a class does nothing, and vice versa"


class TestUnauthenticatedEndpoints:
    def test_registration_is_throttled(self, api_client, settings):
        body = {"email": "spam@example.com"}
        send = lambda: api_client.post(reverse("register"), body, format="json")  # noqa: E731

        assert exhaust(send, limit(settings, "registration")) == 429

    def test_login_is_throttled(self, api_client, settings):
        body = {"email": "nobody@example.com", "password": "WrongPass123!"}
        send = lambda: api_client.post(reverse("login"), body, format="json")  # noqa: E731

        assert exhaust(send, limit(settings, "login")) == 429

    def test_submitting_a_verification_code_is_throttled(self, api_client, settings):
        body = {"email": "nobody@example.com", "code": "000000"}
        send = lambda: api_client.post(reverse("verify-email"), body, format="json")  # noqa: E731

        assert exhaust(send, limit(settings, "code_submit")) == 429

    def test_requesting_a_verification_code_is_throttled(self, api_client, settings):
        body = {"email": "nobody@example.com"}
        send = lambda: api_client.post(reverse("resend-verification"), body, format="json")  # noqa: E731

        assert exhaust(send, limit(settings, "code_request")) == 429

    def test_requesting_a_password_reset_is_throttled(self, api_client, settings):
        body = {"email": "nobody@example.com"}
        send = lambda: api_client.post(reverse("password-reset-request"), body, format="json")  # noqa: E731

        assert exhaust(send, limit(settings, "password_reset")) == 429

    def test_reset_request_and_confirm_share_one_bucket(self, api_client, settings):
        """Both use the `password_reset` scope, so the two together cannot exceed the rate."""
        for _ in range(limit(settings, "password_reset")):
            api_client.post(reverse("password-reset-request"), {"email": "a@example.com"}, format="json")

        response = api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": "a@example.com",
                "code": "000000",
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        assert response.status_code == 429


class TestTokenEndpoints:
    def test_refresh_is_throttled(self, api_client, settings):
        send = lambda: api_client.post(reverse("token_refresh"), {}, format="json")  # noqa: E731

        assert exhaust(send, limit(settings, "token_refresh")) == 429

    def test_refresh_and_logout_share_one_bucket(self, api_client, settings):
        for _ in range(limit(settings, "token_refresh")):
            api_client.post(reverse("token_refresh"), {}, format="json")

        assert api_client.post(reverse("token_blacklist"), {}, format="json").status_code == 429


class TestAuthenticatedEndpoints:
    def test_profile_reads_are_throttled_per_user(self, auth_client, settings):
        send = lambda: auth_client.get(reverse("me"))  # noqa: E731

        assert exhaust(send, limit(settings, "user_info")) == 429

    def test_one_users_limit_does_not_affect_another(self, api_client, base_user, second_user, settings):
        """`user_info` is a UserRateThrottle, so the bucket is per account, not per IP."""
        api_client.force_authenticate(user=base_user)
        for _ in range(limit(settings, "user_info") + 1):
            api_client.get(reverse("me"))

        api_client.force_authenticate(user=second_user)
        assert api_client.get(reverse("me")).status_code == 200


class TestGoogleThrottling:
    def test_google_login_redirects_instead_of_returning_json(self, api_client, settings):
        """
        A browser navigation must never render a DRF error body. Guardrail: the
        `_BrowserOAuthErrorMixin` turns a 429 into a redirect the frontend can handle.
        """
        for _ in range(limit(settings, "google_auth")):
            api_client.get(reverse("google-oauth-login"))

        response = api_client.get(reverse("google-oauth-login"))

        assert response.status_code == 302
        assert response.headers["Location"] == f"{settings.FRONTEND_URL}/login?error=google_rate_limit"

    def test_the_exchange_endpoint_returns_json_because_it_is_fetched(self, api_client, settings):
        for _ in range(limit(settings, "google_auth")):
            api_client.get(reverse("google-oauth-login"))

        response = api_client.post(reverse("google-oauth-exchange"), {"code": "x"}, format="json")

        assert response.status_code == 429
