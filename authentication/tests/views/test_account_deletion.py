"""Deleting your own account."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import EmailVerification, PasswordReset
from authentication.utils import REFRESH_COOKIE_NAME, issue_code

User = get_user_model()

pytestmark = pytest.mark.django_db


def delete(client, email, password=None):
    body = {"email": email}
    if password is not None:
        body["password"] = password
    return client.post(reverse("delete-account"), body, format="json")


class TestDeleteAccount:
    def test_the_account_is_gone(self, auth_client, base_user, user_password):
        response = delete(auth_client, base_user.email, user_password)

        assert response.status_code == 204
        assert User.objects.filter(pk=base_user.pk).exists() is False

    def test_related_rows_go_with_it(self, auth_client, base_user, user_password):
        issue_code(EmailVerification, base_user)
        issue_code(PasswordReset, base_user)

        delete(auth_client, base_user.email, user_password)

        assert EmailVerification.objects.filter(user_id=base_user.pk).exists() is False
        assert PasswordReset.objects.filter(user_id=base_user.pk).exists() is False

    def test_outstanding_sessions_are_revoked_first(self, auth_client, base_user, user_password):
        refresh = str(RefreshToken.for_user(base_user))

        delete(auth_client, base_user.email, user_password)

        assert BlacklistedToken.objects.count() == 1

        auth_client.cookies[REFRESH_COOKIE_NAME] = refresh
        assert auth_client.post(reverse("token_refresh"), {}, format="json").status_code == 401

    def test_the_refresh_cookie_is_cleared(self, auth_client, base_user, user_password):
        response = delete(auth_client, base_user.email, user_password)

        assert response.cookies[REFRESH_COOKIE_NAME].value == ""

    def test_the_address_becomes_available_again(self, api_client, auth_client, base_user, user_password):
        email = base_user.email
        delete(auth_client, email, user_password)

        response = api_client.post(
            reverse("register"),
            {
                "email": email,
                "first_name": "Jane",
                "last_name": "Doe",
                "phone_number": "5551234567",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
            format="json",
        )

        assert response.status_code == 201


class TestDeleteAccountConfirmation:
    def test_the_wrong_password_is_refused(self, auth_client, base_user):
        response = delete(auth_client, base_user.email, "WrongPass123!")

        assert response.status_code == 400
        assert User.objects.filter(pk=base_user.pk).exists() is True

    def test_a_missing_password_is_refused(self, auth_client, base_user):
        response = delete(auth_client, base_user.email)

        assert response.status_code == 400
        assert User.objects.filter(pk=base_user.pk).exists() is True

    def test_a_mistyped_address_is_refused(self, auth_client, base_user, user_password):
        response = delete(auth_client, "someone.else@example.com", user_password)

        assert response.status_code == 400
        assert "email" in response.data
        assert User.objects.filter(pk=base_user.pk).exists() is True

    def test_you_cannot_delete_another_account(self, auth_client, base_user, second_user, user_password):
        response = delete(auth_client, second_user.email, user_password)

        assert response.status_code == 400
        assert User.objects.filter(pk=second_user.pk).exists() is True

    def test_requires_authentication(self, api_client, base_user, user_password):
        assert delete(api_client, base_user.email, user_password).status_code == 401


class TestDeleteGoogleAccount:
    @pytest.fixture
    def google_client(self, api_client, db):
        user = User.objects.create_user(
            email="google@example.com",
            first_name="Goo",
            last_name="Gle",
            is_active=True,
            is_verified=True,
            auth_provider=User.AuthProvider.GOOGLE,
        )
        user.set_unusable_password()
        user.save()
        api_client.force_authenticate(user=user)
        return api_client, user

    def test_no_password_is_required(self, google_client):
        client, user = google_client

        response = delete(client, user.email)

        assert response.status_code == 204
        assert User.objects.filter(pk=user.pk).exists() is False

    def test_the_address_must_still_match(self, google_client):
        client, user = google_client

        response = delete(client, "someone.else@example.com")

        assert response.status_code == 400
        assert User.objects.filter(pk=user.pk).exists() is True
