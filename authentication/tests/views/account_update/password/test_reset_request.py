"""Requesting a password-reset code."""

import pytest
from django.urls import reverse

from authentication.models import PasswordReset

pytestmark = pytest.mark.django_db


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
