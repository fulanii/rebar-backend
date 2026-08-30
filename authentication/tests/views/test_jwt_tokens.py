"""The token endpoints and the refresh-cookie contract."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from authentication.utils import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH

pytestmark = pytest.mark.django_db


def login(client, user, password):
    """Sign in and leave the refresh cookie on the client, as a browser would."""
    return client.post(reverse("login"), {"email": user.email, "password": password}, format="json")


class TestTokenObtain:
    def test_returns_access_and_sets_the_cookie(self, api_client, base_user, user_password):
        response = api_client.post(
            reverse("token_obtain_pair"),
            {"email": base_user.email, "password": user_password},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["access"]
        assert "refresh" not in response.data
        assert REFRESH_COOKIE_NAME in response.cookies

    def test_bad_credentials_set_no_cookie(self, api_client, base_user):
        response = api_client.post(
            reverse("token_obtain_pair"),
            {"email": base_user.email, "password": "WrongPass123!"},
            format="json",
        )

        assert response.status_code == 401
        assert REFRESH_COOKIE_NAME not in response.cookies


class TestTokenRefresh:
    def test_refreshes_from_the_cookie_with_no_body(self, api_client, base_user, user_password):
        login(api_client, base_user, user_password)

        response = api_client.post(reverse("token_refresh"), {}, format="json")

        assert response.status_code == 200
        assert response.data["access"]

    def test_rotates_the_refresh_token(self, api_client, base_user, user_password):
        login_response = login(api_client, base_user, user_password)
        original = login_response.cookies[REFRESH_COOKIE_NAME].value

        response = api_client.post(reverse("token_refresh"), {}, format="json")
        rotated = response.cookies[REFRESH_COOKIE_NAME].value

        assert rotated != original

    def test_the_replaced_token_stops_working(self, api_client, base_user, user_password):
        login_response = login(api_client, base_user, user_password)
        original = login_response.cookies[REFRESH_COOKIE_NAME].value

        api_client.post(reverse("token_refresh"), {}, format="json")

        replay = APIClient()
        replay.cookies[REFRESH_COOKIE_NAME] = original
        assert replay.post(reverse("token_refresh"), {}, format="json").status_code == 401

    def test_missing_cookie_is_a_401_not_a_500(self, api_client):
        response = api_client.post(reverse("token_refresh"), {}, format="json")

        assert response.status_code == 401
        assert "detail" in response.data

    def test_a_garbage_cookie_is_rejected(self, api_client):
        api_client.cookies[REFRESH_COOKIE_NAME] = "not-a-token"

        response = api_client.post(reverse("token_refresh"), {}, format="json")

        assert response.status_code == 401


class TestTokenBlacklist:
    def test_logout_clears_the_cookie(self, api_client, base_user, user_password):
        login(api_client, base_user, user_password)

        response = api_client.post(reverse("token_blacklist"), {}, format="json")

        assert response.status_code == 205
        assert response.cookies[REFRESH_COOKIE_NAME].value == ""

    def test_the_deleted_cookie_matches_the_path_it_was_set_with(self, api_client, base_user, user_password):
        login(api_client, base_user, user_password)

        response = api_client.post(reverse("token_blacklist"), {}, format="json")

        assert response.cookies[REFRESH_COOKIE_NAME]["path"] == REFRESH_COOKIE_PATH

    def test_the_token_cannot_be_used_after_logout(self, api_client, base_user, user_password):
        login(api_client, base_user, user_password)
        stolen = api_client.cookies[REFRESH_COOKIE_NAME].value

        api_client.post(reverse("token_blacklist"), {}, format="json")

        attacker = APIClient()
        attacker.cookies[REFRESH_COOKIE_NAME] = stolen
        assert attacker.post(reverse("token_refresh"), {}, format="json").status_code == 401

    def test_logout_without_a_cookie_still_succeeds(self, api_client):
        response = api_client.post(reverse("token_blacklist"), {}, format="json")

        assert response.status_code == 205
