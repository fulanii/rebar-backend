"""The suspension gate. Proves SuspensionAwareJWTAuthentication is the project default."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.utils import REFRESH_COOKIE_NAME

pytestmark = pytest.mark.django_db


def client_with_real_token(user):
    """
    A client carrying a genuine access token.

    `force_authenticate` bypasses the authentication class entirely, so it cannot be
    used here, the authentication class is exactly what we are testing.
    """
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


class TestSuspension:
    def test_a_normal_user_is_allowed_through(self, base_user):
        response = client_with_real_token(base_user).get(reverse("me"))

        assert response.status_code == 200

    def test_suspension_takes_effect_on_the_very_next_request(self, base_user):
        client = client_with_real_token(base_user)
        assert client.get(reverse("me")).status_code == 200

        base_user.is_suspended = True
        base_user.save(update_fields=["is_suspended"])

        response = client.get(reverse("me"))

        assert response.status_code == 401
        assert response.data["code"] == "account_suspended"

    def test_a_deactivated_user_is_rejected(self, base_user):
        client = client_with_real_token(base_user)

        base_user.is_active = False
        base_user.save(update_fields=["is_active"])

        assert client.get(reverse("me")).status_code == 401


class TestSuspendedAccountsCannotSignIn:
    """
    The flag has to be read on the way in as well as on the way through.

    The authentication class only sees requests that already carry a token, so without
    a check at login a suspended account still gets a 200, a fresh access token and a
    refresh cookie. Every one of those tokens is inert, but the account is told it
    signed in, `last_login` moves, and "when did this account last sign in" stops being
    a true answer during exactly the investigation that led to the suspension.
    """

    def test_login_refuses_a_suspended_account(self, api_client, base_user, user_password):
        base_user.is_suspended = True
        base_user.save(update_fields=["is_suspended"])

        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": user_password}, format="json"
        )

        assert response.status_code == 400
        assert "suspended" in str(response.data).lower()

    def test_no_token_and_no_cookie_are_issued(self, api_client, base_user, user_password):
        base_user.is_suspended = True
        base_user.save(update_fields=["is_suspended"])

        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": user_password}, format="json"
        )

        assert "access" not in response.data
        assert REFRESH_COOKIE_NAME not in response.cookies

    def test_the_last_login_timestamp_does_not_move(self, api_client, base_user, user_password):
        base_user.is_suspended = True
        base_user.save(update_fields=["is_suspended"])

        api_client.post(reverse("login"), {"email": base_user.email, "password": user_password}, format="json")

        base_user.refresh_from_db()
        assert base_user.last_login is None

    def test_a_wrong_password_still_says_nothing_about_the_account(self, api_client, base_user):
        """Suspension is not a fact to hand out to somebody who cannot prove the password."""
        base_user.is_suspended = True
        base_user.save(update_fields=["is_suspended"])

        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": "WrongPass123!"}, format="json"
        )

        assert "suspended" not in str(response.data).lower()

    def test_signing_in_works_again_once_the_suspension_is_lifted(self, api_client, base_user, user_password):
        base_user.is_suspended = True
        base_user.save(update_fields=["is_suspended"])
        base_user.is_suspended = False
        base_user.save(update_fields=["is_suspended"])

        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": user_password}, format="json"
        )

        assert response.status_code == 200
