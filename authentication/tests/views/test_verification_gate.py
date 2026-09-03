"""
The verification gate, on every door that issues or accepts a token.

Registration leaves an account `is_active=False`, and Django's own backend refuses to
authenticate it, so for most of this app's life `is_verified` had nothing to enforce.
It does now: an operator can activate an account without its address ever having been
proven, and `is_active` alone would let that account sign in, or keep signing in on a
token it already holds.

Each test here creates the state that flag combination describes, active but unproven,
which is the state no normal flow produces and every one of these doors has to refuse.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


@pytest.fixture
def activated_but_unproven(base_user):
    """An account somebody switched on without the address ever being verified."""
    base_user.is_verified = False
    base_user.save(update_fields=["is_verified"])
    return base_user


class TestSignIn:
    def test_login_refuses_an_unproven_address(self, api_client, activated_but_unproven, user_password):
        response = api_client.post(
            reverse("login"),
            {"email": activated_but_unproven.email, "password": user_password},
            format="json",
        )

        assert response.status_code == 400
        assert "verify" in str(response.data).lower()

    def test_login_still_works_once_the_address_is_proven(self, api_client, base_user, user_password):
        """The gate has to let the ordinary case through, or it is just an outage."""
        response = api_client.post(
            reverse("login"),
            {"email": base_user.email, "password": user_password},
            format="json",
        )

        assert response.status_code == 200
        assert "access" in response.data


class TestTokensAlreadyIssued:
    def test_a_token_stops_working_the_moment_verification_is_taken_away(self, base_user):
        """
        A JWT outlives the row it was minted from, so the check has to run per request.

        Without it, unverifying an account leaves whoever holds its access token a full
        token lifetime of unimpeded use.
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(base_user).access_token}")

        assert client.get(reverse("me")).status_code == 200

        base_user.is_verified = False
        base_user.save(update_fields=["is_verified"])

        response = client.get(reverse("me"))

        assert response.status_code == 401
        assert response.data["code"] == "email_not_verified"
