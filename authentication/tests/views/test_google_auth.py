"""The Google OAuth flow, with Google itself patched out."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse

from authentication.utils import REFRESH_COOKIE_NAME

User = get_user_model()

pytestmark = pytest.mark.django_db

GOOGLE_IDENTITY = {
    "email": "googler@example.com",
    "given_name": "Goog",
    "family_name": "Ler",
}


def start_login(api_client):
    """Hit the login endpoint and return the `state` it issued."""
    response = api_client.get(reverse("google-oauth-login"))
    location = response.headers["Location"]
    return location.split("state=")[1].split("&")[0]


def complete_callback(api_client, state, identity=None):
    """Run the callback with Google's responses patched out."""
    with (
        patch("authentication.views.google_auth.callback.exchange_code_for_tokens", return_value={"id_token": "fake"}),
        patch(
            "authentication.views.google_auth.callback.id_token.verify_oauth2_token",
            return_value=identity or GOOGLE_IDENTITY,
        ),
    ):
        return api_client.get(reverse("google-oauth-callback"), {"code": "auth-code", "state": state})


class TestLoginRedirect:
    def test_redirects_to_google(self, api_client):
        response = api_client.get(reverse("google-oauth-login"))

        assert response.status_code == 302
        assert response.headers["Location"].startswith("https://accounts.google.com/")

    def test_issues_a_state_and_remembers_it(self, api_client):
        state = start_login(api_client)

        assert cache.get(f"google_oauth_state:{state}") is not None

    def test_each_login_gets_a_different_state(self, api_client):
        assert start_login(api_client) != start_login(api_client)


class TestCallback:
    def test_creates_the_user_and_redirects_with_a_handoff_code(self, api_client, settings):
        state = start_login(api_client)

        response = complete_callback(api_client, state)

        assert response.status_code == 302
        assert response.headers["Location"].startswith(f"{settings.FRONTEND_URL}/auth/callback#code=")
        assert User.objects.filter(email="googler@example.com").exists()

    def test_the_new_account_is_active_and_verified(self, api_client):
        complete_callback(api_client, start_login(api_client))
        user = User.objects.get(email="googler@example.com")

        assert user.is_active is True
        assert user.is_verified is True
        assert user.auth_provider == User.AuthProvider.GOOGLE

    def test_the_new_account_has_no_usable_password(self, api_client):
        complete_callback(api_client, start_login(api_client))

        assert User.objects.get(email="googler@example.com").has_usable_password() is False

    def test_an_existing_account_is_reused_not_duplicated(self, api_client, base_user):
        identity = {"email": base_user.email, "given_name": "Test", "family_name": "User"}

        complete_callback(api_client, start_login(api_client), identity)

        assert User.objects.filter(email=base_user.email).count() == 1

    def test_signing_in_with_google_verifies_a_pending_account(self, api_client, unverified_user):
        identity = {"email": unverified_user.email, "given_name": "P", "family_name": "U"}

        complete_callback(api_client, start_login(api_client), identity)

        unverified_user.refresh_from_db()
        assert unverified_user.is_active is True
        assert unverified_user.is_verified is True

    def test_the_state_is_single_use(self, api_client):
        state = start_login(api_client)
        complete_callback(api_client, state)

        replay = complete_callback(api_client, state)

        assert replay.headers["Location"].endswith("/login?error=google")

    def test_a_forged_state_is_refused(self, api_client, settings):
        response = complete_callback(api_client, "state-we-never-issued")

        assert response.status_code == 302
        assert response.headers["Location"] == f"{settings.FRONTEND_URL}/login?error=google"

    def test_a_cancelled_consent_redirects_to_the_frontend(self, api_client, settings):
        response = api_client.get(reverse("google-oauth-callback"), {"error": "access_denied"})

        assert response.headers["Location"] == f"{settings.FRONTEND_URL}/login?error=google"

    def test_a_failed_exchange_redirects_rather_than_500s(self, api_client, settings):
        import requests

        state = start_login(api_client)

        with patch(
            "authentication.views.google_auth.callback.exchange_code_for_tokens",
            side_effect=requests.RequestException("google is down"),
        ):
            response = api_client.get(reverse("google-oauth-callback"), {"code": "c", "state": state})

        assert response.status_code == 302
        assert response.headers["Location"] == f"{settings.FRONTEND_URL}/login?error=google"

    def test_an_identity_without_an_email_is_refused(self, api_client, settings):
        state = start_login(api_client)

        response = complete_callback(api_client, state, {"given_name": "No", "family_name": "Email"})

        assert response.headers["Location"] == f"{settings.FRONTEND_URL}/login?error=google"

    def test_no_jwt_ever_appears_in_the_redirect_url(self, api_client):
        response = complete_callback(api_client, start_login(api_client))

        assert "access" not in response.headers["Location"]
        assert "eyJ" not in response.headers["Location"]


class TestExchange:
    def handoff_code(self, api_client):
        response = complete_callback(api_client, start_login(api_client))
        return response.headers["Location"].split("#code=")[1]

    def test_returns_an_access_token_and_sets_the_cookie(self, api_client):
        code = self.handoff_code(api_client)

        response = api_client.post(reverse("google-oauth-exchange"), {"code": code}, format="json")

        assert response.status_code == 200
        assert response.data["access"]
        assert response.data["user_data"]["email"] == "googler@example.com"
        assert REFRESH_COOKIE_NAME in response.cookies

    def test_the_refresh_token_is_not_in_the_body(self, api_client):
        code = self.handoff_code(api_client)

        response = api_client.post(reverse("google-oauth-exchange"), {"code": code}, format="json")

        assert "refresh" not in response.data

    def test_the_code_is_single_use(self, api_client):
        code = self.handoff_code(api_client)
        api_client.post(reverse("google-oauth-exchange"), {"code": code}, format="json")

        second = api_client.post(reverse("google-oauth-exchange"), {"code": code}, format="json")

        assert second.status_code == 400

    def test_an_unknown_code_is_refused(self, api_client):
        response = api_client.post(reverse("google-oauth-exchange"), {"code": "never-issued"}, format="json")

        assert response.status_code == 400

    def test_an_expired_code_is_refused(self, api_client):
        code = self.handoff_code(api_client)
        cache.delete(f"google_oauth_exchange:{code}")

        response = api_client.post(reverse("google-oauth-exchange"), {"code": code}, format="json")

        assert response.status_code == 400

    def test_the_code_is_required(self, api_client):
        response = api_client.post(reverse("google-oauth-exchange"), {}, format="json")

        assert response.status_code == 400


class TestAdoptingAnExistingAccount:
    """
    Signing in with Google against an address that already has a row.

    Google proves the person owns the address. It proves nothing about who set the
    password on a row that was never verified.
    """

    def test_an_unverified_account_is_activated(self, api_client, unverified_user):
        complete_callback(
            api_client,
            start_login(api_client),
            {"email": unverified_user.email, "given_name": "P", "family_name": "U"},
        )
        unverified_user.refresh_from_db()

        assert unverified_user.is_active is True
        assert unverified_user.is_verified is True

    def test_a_verified_account_keeps_its_password(self, api_client, base_user, user_password):
        """Google sign-in is a second way in, not a reason to lock someone out of their password."""
        complete_callback(
            api_client,
            start_login(api_client),
            {"email": base_user.email, "given_name": "T", "family_name": "U"},
        )
        base_user.refresh_from_db()

        assert base_user.check_password(user_password) is True

    def test_adopting_an_unverified_account_discards_its_password(self, api_client, db):
        """
        The attack this guards against:

        1. An attacker registers the victim's address with a password they choose. The
           account exists, inactive, unverified -- they cannot verify it.
        2. The victim later signs in with Google. The row is adopted and activated.
        3. The attacker's password still works, and they now hold a live account.
        """
        attacker_password = "AttackerPass123!"
        User.objects.create_user(
            email="victim@example.com",
            password=attacker_password,
            first_name="Victim",
            last_name="User",
            phone_number="5551230000",
        )

        complete_callback(
            api_client,
            start_login(api_client),
            {"email": "victim@example.com", "given_name": "Victim", "family_name": "User"},
        )

        victim = User.objects.get(email="victim@example.com")
        assert victim.check_password(attacker_password) is False
