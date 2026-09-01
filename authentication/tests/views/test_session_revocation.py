"""
Access tokens issued before a revocation.

Blacklisting only reaches refresh tokens, which are stored. An access token is stored
nowhere, so `sessions_revoked_at` on the user row is the only thing that can stop one
before it expires, without it a password reset leaves a 30-minute tail.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from authentication.models import PasswordReset
from authentication.utils import issue_code, revoke_sessions

pytestmark = pytest.mark.django_db


def bearer(api_client, user):
    """Give `api_client` a real access token for `user`, not a forced login."""
    token = RefreshToken.for_user(user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


class TestStaleAccessTokens:
    def test_a_token_issued_before_revocation_is_refused(self, api_client, base_user):
        client = bearer(api_client, base_user)
        assert client.get(reverse("me")).status_code == 200

        revoke_sessions(base_user)

        response = client.get(reverse("me"))
        assert response.status_code == 401
        assert response.data["code"] == "session_revoked"

    def test_a_token_issued_after_revocation_still_works(self, api_client, base_user):
        revoke_sessions(base_user)
        base_user.refresh_from_db()
        base_user.sessions_revoked_at = timezone.now() - timedelta(minutes=1)
        base_user.save(update_fields=["sessions_revoked_at"])

        assert bearer(api_client, base_user).get(reverse("me")).status_code == 200

    def test_an_untouched_account_is_unaffected(self, api_client, base_user):
        assert base_user.sessions_revoked_at is None
        assert bearer(api_client, base_user).get(reverse("me")).status_code == 200

    def test_other_users_are_unaffected(self, api_client, base_user, second_user):
        client = bearer(api_client, second_user)

        revoke_sessions(base_user)

        assert client.get(reverse("me")).status_code == 200


class TestPasswordResetEndsTheTail:
    def test_a_reset_kills_a_live_access_token(self, api_client, base_user):
        client = bearer(api_client, base_user)
        code = issue_code(PasswordReset, base_user)

        api_client.post(
            reverse("password-reset-confirm"),
            {
                "email": base_user.email,
                "code": code,
                "new_password": "BrandNewPass456!",
                "confirm_password": "BrandNewPass456!",
            },
            format="json",
        )

        assert client.get(reverse("me")).status_code == 401

    def test_a_password_change_leaves_your_token_alone(self, api_client, base_user, user_password):
        client = bearer(api_client, base_user)

        response = client.post(
            reverse("change-password"),
            {
                "current_password": user_password,
                "new_password": "BrandNewPass456!",
                "confirm_password": "BrandNewPass456!",
            },
            format="json",
        )

        assert response.status_code == 200
        assert client.get(reverse("me")).status_code == 200
        base_user.refresh_from_db()
        assert base_user.sessions_revoked_at is None


class TestRevocationStamp:
    def test_the_stamp_is_written_when_sessions_are_revoked(self, base_user):
        before = timezone.now()

        revoke_sessions(base_user)

        base_user.refresh_from_db()
        assert base_user.sessions_revoked_at >= before
