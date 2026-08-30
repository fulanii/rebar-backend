"""Password reset and password change endpoints."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from authentication.models import PasswordReset

pytestmark = pytest.mark.django_db


@pytest.fixture
def reset_code(base_user):
    """A live reset code for `base_user`. Returns the raw digits."""
    from authentication.utils import issue_code

    with patch("authentication.utils.generate_code.secrets.randbelow", return_value=123456):
        return issue_code(PasswordReset, base_user)


class TestResetRequest:
    def test_issues_a_code_and_emails_it(self, api_client, base_user, block_outbound_email):
        response = api_client.post(reverse("password-reset-request"), {"email": base_user.email}, format="json")

        assert response.status_code == 200
        assert PasswordReset.objects.filter(user=base_user).exists()
        assert block_outbound_email.called

    def test_unknown_address_returns_200_and_sends_nothing(self, api_client, block_outbound_email):
        response = api_client.post(reverse("password-reset-request"), {"email": "nobody@example.com"}, format="json")

        assert response.status_code == 200
        assert not block_outbound_email.called

    def test_google_account_gets_no_reset_code(self, api_client, db, block_outbound_email):
        from authentication.utils import get_or_create_google_user

        user, _ = get_or_create_google_user("g@example.com", "G", "User")
        block_outbound_email.reset_mock()

        response = api_client.post(reverse("password-reset-request"), {"email": user.email}, format="json")

        assert response.status_code == 200
        assert not block_outbound_email.called

    def test_a_new_request_invalidates_the_previous_code(self, api_client, base_user, reset_code):
        api_client.post(reverse("password-reset-request"), {"email": base_user.email}, format="json")

        response = api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": base_user.email,
                "code": reset_code,
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        assert response.status_code == 400


class TestResetConfirm:
    def test_correct_code_changes_the_password(self, api_client, base_user, reset_code):
        response = api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": base_user.email,
                "code": reset_code,
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        assert response.status_code == 200
        base_user.refresh_from_db()
        assert base_user.check_password("BrandNewPass123!") is True

    def test_the_code_cannot_be_replayed(self, api_client, base_user, reset_code):
        body = {
            "email": base_user.email,
            "code": reset_code,
            "new_password": "BrandNewPass123!",
            "confirm_password": "BrandNewPass123!",
        }
        api_client.post(reverse("password-reset-confirm"), body, format="json")

        second = api_client.post(reverse("password-reset-confirm"), body, format="json")

        assert second.status_code == 400

    def test_wrong_code_leaves_the_password_alone(self, api_client, base_user, reset_code, user_password):
        response = api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": base_user.email,
                "code": "999999",
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        assert response.status_code == 400
        base_user.refresh_from_db()
        assert base_user.check_password(user_password) is True

    def test_expired_code_is_rejected(self, api_client, base_user, reset_code):
        PasswordReset.objects.filter(user=base_user).update(expires_at=timezone.now() - timedelta(seconds=1))

        response = api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": base_user.email,
                "code": reset_code,
                "new_password": "BrandNewPass123!",
                "confirm_password": "BrandNewPass123!",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_weak_new_password_is_rejected(self, api_client, base_user, reset_code):
        response = api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": base_user.email,
                "code": reset_code,
                "new_password": "weakpass",
                "confirm_password": "weakpass",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "new_password" in response.data

    def test_mismatched_confirmation_is_rejected(self, api_client, base_user, reset_code):
        response = api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": base_user.email,
                "code": reset_code,
                "new_password": "BrandNewPass123!",
                "confirm_password": "DifferentPass123!",
            },
            format="json",
        )

        assert response.status_code == 400


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
