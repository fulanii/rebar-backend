"""The login endpoint."""

import pytest
from django.urls import reverse

from authentication.utils import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH

pytestmark = pytest.mark.django_db


class TestLoginSuccess:
    def test_returns_an_access_token_and_profile(self, api_client, base_user, user_password):
        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": user_password}, format="json"
        )

        assert response.status_code == 200
        assert response.data["access"]
        assert response.data["user_data"]["email"] == base_user.email

    def test_refresh_token_is_never_in_the_body(self, api_client, base_user, user_password):
        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": user_password}, format="json"
        )

        assert "refresh" not in response.data

    def test_refresh_cookie_is_httponly_and_path_scoped(self, api_client, base_user, user_password):
        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": user_password}, format="json"
        )

        cookie = response.cookies[REFRESH_COOKIE_NAME]
        assert cookie["httponly"] is True
        assert cookie["path"] == REFRESH_COOKIE_PATH
        assert cookie["samesite"] == "Lax"

    def test_email_is_case_insensitive(self, api_client, base_user, user_password):
        response = api_client.post(
            reverse("login"), {"email": base_user.email.upper(), "password": user_password}, format="json"
        )

        assert response.status_code == 200

    def test_password_is_not_echoed_back(self, api_client, base_user, user_password):
        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": user_password}, format="json"
        )

        assert "password" not in response.data


class TestLoginFailure:
    def test_wrong_password_is_rejected(self, api_client, base_user):
        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": "WrongPass123!"}, format="json"
        )

        assert response.status_code == 400
        assert "access" not in response.data

    def test_unknown_email_and_wrong_password_give_the_same_message(self, api_client, base_user):
        wrong_password = api_client.post(
            reverse("login"), {"email": base_user.email, "password": "WrongPass123!"}, format="json"
        )
        unknown_email = api_client.post(
            reverse("login"), {"email": "nobody@example.com", "password": "WrongPass123!"}, format="json"
        )

        assert wrong_password.data == unknown_email.data

    def test_unverified_account_is_told_to_verify(self, api_client, unverified_user, user_password):
        response = api_client.post(
            reverse("login"), {"email": unverified_user.email, "password": user_password}, format="json"
        )

        assert response.status_code == 400
        assert "verify" in str(response.data).lower()

    def test_unverified_account_with_wrong_password_does_not_leak_its_existence(self, api_client, unverified_user):
        response = api_client.post(
            reverse("login"), {"email": unverified_user.email, "password": "WrongPass123!"}, format="json"
        )

        assert "verify" not in str(response.data).lower()

    def test_no_cookie_is_set_on_failure(self, api_client, base_user):
        response = api_client.post(
            reverse("login"), {"email": base_user.email, "password": "WrongPass123!"}, format="json"
        )

        assert REFRESH_COOKIE_NAME not in response.cookies


class TestLastLogin:
    def test_a_successful_login_is_recorded(self, api_client, base_user, user_password):
        assert base_user.last_login is None

        api_client.post(reverse("login"), {"email": base_user.email, "password": user_password}, format="json")

        base_user.refresh_from_db()
        assert base_user.last_login is not None

    def test_a_failed_login_is_not_recorded(self, api_client, base_user):
        api_client.post(reverse("login"), {"email": base_user.email, "password": "WrongPass123!"}, format="json")

        base_user.refresh_from_db()
        assert base_user.last_login is None

    def test_the_token_endpoint_records_it_too(self, api_client, base_user, user_password):
        api_client.post(
            reverse("token_obtain_pair"), {"email": base_user.email, "password": user_password}, format="json"
        )

        base_user.refresh_from_db()
        assert base_user.last_login is not None
