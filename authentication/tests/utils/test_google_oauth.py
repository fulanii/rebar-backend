"""The Google helpers, unit-tested away from the request cycle."""

from urllib.parse import parse_qs, urlparse

import pytest
import requests

from authentication.models import CustomUser
from authentication.utils import (
    build_authorize_url,
    build_user_payload,
    exchange_code_for_tokens,
    get_or_create_google_user,
    issue_jwt_payload,
)

CALLBACK = "http://localhost:8000/auth/google/callback/"


class TestAuthorizeUrl:
    def test_points_at_google(self, settings):
        settings.GOOGLE_CLIENT_ID = "client-123"

        assert build_authorize_url(CALLBACK, "state-abc").startswith("https://accounts.google.com/")

    def test_carries_the_client_id_redirect_and_state(self, settings):
        settings.GOOGLE_CLIENT_ID = "client-123"

        params = parse_qs(urlparse(build_authorize_url(CALLBACK, "state-abc")).query)

        assert params["client_id"] == ["client-123"]
        assert params["redirect_uri"] == [CALLBACK]
        assert params["state"] == ["state-abc"]
        assert params["response_type"] == ["code"]

    def test_asks_for_the_account_chooser(self, settings):
        """Otherwise a shared machine silently signs in as whoever used it last."""
        settings.GOOGLE_CLIENT_ID = "client-123"

        params = parse_qs(urlparse(build_authorize_url(CALLBACK, "s")).query)

        assert params["prompt"] == ["select_account"]

    def test_requests_only_identity_scopes(self, settings):
        settings.GOOGLE_CLIENT_ID = "client-123"

        params = parse_qs(urlparse(build_authorize_url(CALLBACK, "s")).query)

        assert set(params["scope"][0].split()) == {"openid", "email", "profile"}


class TestExchangeCodeForTokens:
    def test_posts_the_client_secret_with_a_timeout(self, settings, monkeypatch):
        settings.GOOGLE_CLIENT_ID = "client-123"
        settings.GOOGLE_CLIENT_SECRET = "secret-xyz"
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"id_token": "jwt"}

        def fake_post(url, data=None, timeout=None):
            captured.update(url=url, data=data, timeout=timeout)
            return FakeResponse()

        monkeypatch.setattr(requests, "post", fake_post)

        assert exchange_code_for_tokens("auth-code", CALLBACK) == {"id_token": "jwt"}
        assert captured["data"]["client_secret"] == "secret-xyz"
        assert captured["data"]["redirect_uri"] == CALLBACK
        # An unbounded call can hang a worker until it times out at the server.
        assert captured["timeout"] is not None

    def test_an_http_error_propagates(self, monkeypatch):
        class FakeResponse:
            def raise_for_status(self):
                raise requests.RequestException("502")

        monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse())

        with pytest.raises(requests.RequestException):
            exchange_code_for_tokens("auth-code", CALLBACK)


@pytest.mark.django_db
class TestGetOrCreateGoogleUser:
    def test_creates_a_new_account(self):
        user, created = get_or_create_google_user("new@example.com", "New", "User")

        assert created is True
        assert user.email == "new@example.com"
        assert user.first_name == "New"
        assert user.auth_provider == CustomUser.AuthProvider.GOOGLE

    def test_a_new_account_is_active_and_verified(self):
        user, _ = get_or_create_google_user("new@example.com", "New", "User")

        assert user.is_active is True
        assert user.is_verified is True

    def test_a_new_account_has_no_usable_password(self):
        user, _ = get_or_create_google_user("new@example.com", "New", "User")

        assert user.has_usable_password() is False

    def test_the_email_is_normalized(self):
        user, _ = get_or_create_google_user("  NEW@Example.COM  ", "New", "User")

        assert user.email == "new@example.com"

    def test_a_missing_name_falls_back_to_the_local_part(self):
        user, _ = get_or_create_google_user("solo@example.com", "", "")

        assert user.first_name == "solo"

    def test_an_existing_account_is_reused(self, base_user):
        user, created = get_or_create_google_user(base_user.email, "Ignored", "Ignored")

        assert created is False
        assert user.pk == base_user.pk

    def test_an_existing_profile_is_not_overwritten_by_google(self, base_user):
        get_or_create_google_user(base_user.email, "Google", "Name")
        base_user.refresh_from_db()

        assert base_user.first_name == "Test"

    def test_a_pending_account_is_activated(self, unverified_user):
        get_or_create_google_user(unverified_user.email, "P", "U")
        unverified_user.refresh_from_db()

        assert unverified_user.is_active is True
        assert unverified_user.is_verified is True


@pytest.mark.django_db
class TestJwtPayload:
    def test_carries_both_tokens_and_the_profile(self, base_user):
        payload = issue_jwt_payload(base_user)

        assert payload["access"]
        assert payload["refresh"]
        assert payload["user_data"]["email"] == base_user.email

    def test_the_profile_omits_permission_flags(self, base_user):
        payload = build_user_payload(base_user)

        for field in ("password", "is_staff", "is_superuser", "is_suspended"):
            assert field not in payload

    def test_adopting_a_pending_account_discards_its_password(self, unverified_user, user_password):
        get_or_create_google_user(unverified_user.email, "P", "U")
        unverified_user.refresh_from_db()

        assert unverified_user.has_usable_password() is False
        assert unverified_user.check_password(user_password) is False

    def test_adopting_a_pending_account_marks_it_as_google(self, unverified_user):
        get_or_create_google_user(unverified_user.email, "P", "U")
        unverified_user.refresh_from_db()

        assert unverified_user.auth_provider == CustomUser.AuthProvider.GOOGLE

    def test_a_verified_account_keeps_its_password_and_provider(self, base_user, user_password):
        get_or_create_google_user(base_user.email, "T", "U")
        base_user.refresh_from_db()

        assert base_user.check_password(user_password) is True
        assert base_user.auth_provider == CustomUser.AuthProvider.EMAIL
