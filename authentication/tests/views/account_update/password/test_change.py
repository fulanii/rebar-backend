"""Changing a password while signed in."""

import pytest
from django.urls import reverse
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


class TestPasswordChange:
    def test_changes_the_password(self, auth_client, base_user, user_password):
        response = auth_client.post(
            reverse("change-password"),
            {
                "current_password": user_password,
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        assert response.status_code == 200
        base_user.refresh_from_db()
        assert base_user.check_password("BrandNewPass123!") is True

    def test_wrong_current_password_is_rejected(self, auth_client, base_user, user_password):
        response = auth_client.post(
            reverse("change-password"),
            {
                "current_password": "WrongPass123!",
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        assert response.status_code == 400
        base_user.refresh_from_db()
        assert base_user.check_password(user_password) is True

    def test_reusing_the_current_password_is_rejected(self, auth_client, user_password):
        response = auth_client.post(
            reverse("change-password"),
            {
                "current_password": user_password,
                "new_password": user_password,
                "confirm_password": user_password,
            },
            format="json",
        )

        assert response.status_code == 400

    def test_a_notification_is_emailed(self, auth_client, base_user, user_password, block_outbound_email):
        block_outbound_email.reset_mock()

        auth_client.post(
            reverse("change-password"),
            {
                "current_password": user_password,
                "new_password": "BrandNewPass456!",
                "confirm_password": "BrandNewPass456!",
            },
            format="json",
        )

        assert block_outbound_email.called is True

    def test_no_notification_when_the_change_is_rejected(
        self, auth_client, base_user, user_password, block_outbound_email
    ):
        block_outbound_email.reset_mock()

        auth_client.post(
            reverse("change-password"),
            {
                "current_password": "WrongPass123!",
                "new_password": "BrandNewPass456!",
                "confirm_password": "BrandNewPass456!",
            },
            format="json",
        )

        assert block_outbound_email.called is False

    def test_other_sessions_are_left_alone(self, auth_client, base_user, user_password):
        RefreshToken.for_user(base_user)

        auth_client.post(
            reverse("change-password"),
            {
                "current_password": user_password,
                "new_password": "BrandNewPass456!",
                "confirm_password": "BrandNewPass456!",
            },
            format="json",
        )

        assert BlacklistedToken.objects.filter(token__user=base_user).count() == 0

    def test_requires_authentication(self, api_client, user_password):
        response = api_client.post(
            reverse("change-password"),
            {
                "current_password": user_password,
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        assert response.status_code == 401
