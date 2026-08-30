"""Email verification and resend endpoints."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from authentication.models import EmailVerification

pytestmark = pytest.mark.django_db


@pytest.fixture
def pending_code(unverified_user):
    """A live verification code for `unverified_user`. Returns the raw digits."""
    from authentication.utils import issue_code

    with patch("authentication.utils.generate_code.secrets.randbelow", return_value=123456):
        return issue_code(EmailVerification, unverified_user)


class TestVerifyEmail:
    def test_correct_code_activates_the_account(self, api_client, unverified_user, pending_code):
        response = api_client.post(
            reverse("verify-email"),
            {"email": unverified_user.email, "code": pending_code},
            format="json",
        )

        assert response.status_code == 200
        unverified_user.refresh_from_db()
        assert unverified_user.is_active is True
        assert unverified_user.is_verified is True

    def test_the_code_is_burned_after_use(self, api_client, unverified_user, pending_code):
        api_client.post(
            reverse("verify-email"),
            {"email": unverified_user.email, "code": pending_code},
            format="json",
        )

        assert EmailVerification.objects.get(user=unverified_user).used is True

    def test_a_used_code_cannot_be_replayed(self, api_client, unverified_user, pending_code):
        body = {"email": unverified_user.email, "code": pending_code}
        api_client.post(reverse("verify-email"), body, format="json")

        second = api_client.post(reverse("verify-email"), body, format="json")

        assert second.status_code == 400

    def test_wrong_code_is_rejected(self, api_client, unverified_user, pending_code):
        response = api_client.post(
            reverse("verify-email"),
            {"email": unverified_user.email, "code": "999999"},
            format="json",
        )

        assert response.status_code == 400
        unverified_user.refresh_from_db()
        assert unverified_user.is_active is False

    def test_expired_code_is_rejected(self, api_client, unverified_user, pending_code):
        EmailVerification.objects.filter(user=unverified_user).update(expires_at=timezone.now() - timedelta(seconds=1))

        response = api_client.post(
            reverse("verify-email"),
            {"email": unverified_user.email, "code": pending_code},
            format="json",
        )

        assert response.status_code == 400

    def test_unknown_email_gives_the_same_error_as_a_wrong_code(self, api_client, unverified_user, pending_code):
        wrong_code = api_client.post(
            reverse("verify-email"),
            {"email": unverified_user.email, "code": "999999"},
            format="json",
        )
        unknown_email = api_client.post(
            reverse("verify-email"),
            {"email": "nobody@example.com", "code": "999999"},
            format="json",
        )

        assert wrong_code.status_code == unknown_email.status_code == 400
        assert wrong_code.data == unknown_email.data

    @pytest.mark.parametrize("code", ["12345", "1234567", "abcdef", ""])
    def test_malformed_codes_are_rejected(self, api_client, unverified_user, code):
        response = api_client.post(
            reverse("verify-email"),
            {"email": unverified_user.email, "code": code},
            format="json",
        )

        assert response.status_code == 400


class TestResendVerification:
    def test_issues_a_new_code(self, api_client, unverified_user, pending_code):
        api_client.post(reverse("resend-verification"), {"email": unverified_user.email}, format="json")

        verification = EmailVerification.objects.get(user=unverified_user)
        assert verification.check_code(pending_code) is False

    def test_the_previous_code_stops_working(self, api_client, unverified_user, pending_code):
        api_client.post(reverse("resend-verification"), {"email": unverified_user.email}, format="json")

        response = api_client.post(
            reverse("verify-email"),
            {"email": unverified_user.email, "code": pending_code},
            format="json",
        )

        assert response.status_code == 400

    def test_sends_an_email(self, api_client, unverified_user, block_outbound_email):
        block_outbound_email.reset_mock()
        api_client.post(reverse("resend-verification"), {"email": unverified_user.email}, format="json")

        assert block_outbound_email.called

    def test_unknown_address_returns_200_and_sends_nothing(self, api_client, block_outbound_email):
        response = api_client.post(reverse("resend-verification"), {"email": "nobody@example.com"}, format="json")

        assert response.status_code == 200
        assert not block_outbound_email.called

    def test_already_verified_address_returns_200_and_sends_nothing(self, api_client, base_user, block_outbound_email):
        response = api_client.post(reverse("resend-verification"), {"email": base_user.email}, format="json")

        assert response.status_code == 200
        assert not block_outbound_email.called
