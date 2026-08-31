"""Completing a password reset: the code, the attempt limit, and ending every session."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import PasswordReset
from authentication.models.one_time_code import MAX_ATTEMPTS
from authentication.utils import REFRESH_COOKIE_NAME

pytestmark = pytest.mark.django_db


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


class TestResetConfirmAttemptLimit:
    """
    Guardrail: the per-IP throttle cannot see the same code being guessed from a
    thousand addresses. The counter on the code itself can.
    """

    def submit(self, api_client, user, code):
        return api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": user.email,
                "code": code,
                "new_password": "BrandNewPass456!",
                "confirm_password": "BrandNewPass456!",
            },
            format="json",
        )

    def test_a_wrong_code_is_counted(self, api_client, base_user, reset_code, unlimited_requests):
        self.submit(api_client, base_user, "000000")

        assert PasswordReset.objects.get(user=base_user).attempts == 1

    def test_the_code_survives_up_to_the_limit(self, api_client, base_user, reset_code, unlimited_requests):
        for _ in range(MAX_ATTEMPTS - 1):
            self.submit(api_client, base_user, "000000")

        assert self.submit(api_client, base_user, reset_code).status_code == 200

    def test_the_code_dies_at_the_limit(self, api_client, base_user, reset_code, user_password, unlimited_requests):
        for _ in range(MAX_ATTEMPTS):
            assert self.submit(api_client, base_user, "000000").status_code == 400

        response = self.submit(api_client, base_user, reset_code)

        assert response.status_code == 400
        assert response.data["detail"] == "Invalid or expired reset code."
        base_user.refresh_from_db()
        assert base_user.check_password(user_password) is True

    def test_a_new_request_gives_the_user_a_fresh_five(self, api_client, base_user, reset_code, unlimited_requests):
        for _ in range(MAX_ATTEMPTS):
            self.submit(api_client, base_user, "000000")

        api_client.post(reverse("password-reset-request"), {"email": base_user.email}, format="json")

        reset = PasswordReset.objects.get(user=base_user)
        assert reset.attempts == 0
        assert reset.is_valid is True


class TestResetConfirmEndsOtherSessions:
    """
    Guardrail: a reset usually means someone else is in the account. Rotating the
    password while leaving their refresh token alive would defeat the point.
    """

    def confirm(self, api_client, user, code):
        return api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": user.email,
                "code": code,
                "new_password": "BrandNewPass456!",
                "confirm_password": "BrandNewPass456!",
            },
            format="json",
        )

    def test_outstanding_refresh_tokens_are_blacklisted(self, api_client, base_user, reset_code):
        RefreshToken.for_user(base_user)
        RefreshToken.for_user(base_user)

        self.confirm(api_client, base_user, reset_code)

        assert BlacklistedToken.objects.filter(token__user=base_user).count() == 2

    def test_a_stolen_refresh_token_stops_refreshing(self, api_client, base_user, reset_code):
        refresh = str(RefreshToken.for_user(base_user))

        self.confirm(api_client, base_user, reset_code)

        api_client.cookies[REFRESH_COOKIE_NAME] = refresh
        response = api_client.post(reverse("token_refresh"), {}, format="json")

        assert response.status_code == 401

    def test_other_users_keep_their_sessions(self, api_client, base_user, second_user, reset_code):
        RefreshToken.for_user(second_user)

        self.confirm(api_client, base_user, reset_code)

        assert BlacklistedToken.objects.filter(token__user=second_user).count() == 0

    def test_a_notification_is_emailed(self, api_client, base_user, reset_code, block_outbound_email):
        block_outbound_email.reset_mock()

        self.confirm(api_client, base_user, reset_code)

        assert block_outbound_email.called is True

    def test_a_failed_reset_revokes_nothing(self, api_client, base_user, reset_code):
        RefreshToken.for_user(base_user)

        self.confirm(api_client, base_user, "000000")

        assert BlacklistedToken.objects.filter(token__user=base_user).count() == 0
