"""The suspension gate. Proves SuspensionAwareJWTAuthentication is the project default."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


def client_with_real_token(user):
    """
    A client carrying a genuine access token.

    `force_authenticate` bypasses the authentication class entirely, so it cannot be
    used here -- the authentication class is exactly what we are testing.
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
