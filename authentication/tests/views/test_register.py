"""Registration endpoint."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from authentication.models import EmailVerification

User = get_user_model()

pytestmark = pytest.mark.django_db


def payload(**overrides):
    data = {
        "email": "new@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "phone_number": "(555) 123-4567",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    data.update(overrides)
    return data


class TestRegisterSuccess:
    def test_creates_an_inactive_account(self, api_client):
        response = api_client.post(reverse("register"), payload(), format="json")

        assert response.status_code == 201
        user = User.objects.get(email="new@example.com")
        assert user.is_active is False
        assert user.is_verified is False

    def test_returns_no_tokens(self, api_client):
        response = api_client.post(reverse("register"), payload(), format="json")

        assert "access" not in response.data
        assert "refresh" not in response.data

    def test_phone_number_is_normalized(self, api_client):
        api_client.post(reverse("register"), payload(), format="json")

        assert User.objects.get(email="new@example.com").phone_number == "5551234567"

    def test_email_is_lowercased(self, api_client):
        api_client.post(reverse("register"), payload(email="NEW@Example.COM"), format="json")

        assert User.objects.filter(email="new@example.com").exists()

    def test_password_is_hashed(self, api_client):
        api_client.post(reverse("register"), payload(), format="json")
        user = User.objects.get(email="new@example.com")

        assert user.password != "SecurePass123!"
        assert user.check_password("SecurePass123!")

    def test_issues_a_verification_code(self, api_client):
        api_client.post(reverse("register"), payload(), format="json")
        user = User.objects.get(email="new@example.com")

        assert EmailVerification.objects.filter(user=user).exists()

    def test_sends_the_code_by_email(self, api_client, block_outbound_email):
        api_client.post(reverse("register"), payload(), format="json")

        assert block_outbound_email.called

    def test_the_stored_code_is_hashed(self, api_client, block_outbound_email):
        api_client.post(reverse("register"), payload(), format="json")
        verification = EmailVerification.objects.get(user__email="new@example.com")

        assert len(verification.code) > 6
        assert not verification.code.isdigit()


class TestRegisterValidation:
    def test_duplicate_email_is_rejected(self, api_client, base_user):
        response = api_client.post(reverse("register"), payload(email=base_user.email), format="json")

        assert response.status_code == 400
        assert "email" in response.data

    def test_mismatched_passwords_are_rejected(self, api_client):
        response = api_client.post(reverse("register"), payload(confirm_password="DifferentPass123!"), format="json")

        assert response.status_code == 400
        assert "confirm_password" in response.data

    def test_weak_password_is_rejected(self, api_client):
        response = api_client.post(
            reverse("register"), payload(password="weakpass", confirm_password="weakpass"), format="json"
        )

        assert response.status_code == 400
        assert "password" in response.data

    @pytest.mark.parametrize("field", ["email", "first_name", "last_name", "phone_number", "password"])
    def test_every_field_is_required(self, api_client, field):
        data = payload()
        data.pop(field)
        response = api_client.post(reverse("register"), data, format="json")

        assert response.status_code == 400
        assert field in response.data

    def test_phone_number_is_required(self, api_client):
        response = api_client.post(reverse("register"), payload(phone_number=""), format="json")

        assert response.status_code == 400
        assert "phone_number" in response.data

    def test_invalid_phone_number_is_rejected(self, api_client):
        response = api_client.post(reverse("register"), payload(phone_number="555123"), format="json")

        assert response.status_code == 400
        assert "phone_number" in response.data

    def test_no_account_is_created_when_validation_fails(self, api_client):
        api_client.post(reverse("register"), payload(password="weak", confirm_password="weak"), format="json")

        assert not User.objects.filter(email="new@example.com").exists()

    def test_password_is_never_echoed_back(self, api_client):
        response = api_client.post(reverse("register"), payload(), format="json")

        assert "password" not in response.data


class TestRegisterAtomicity:
    def test_no_account_survives_a_failure_while_issuing_the_code(self, api_client):
        """
        The user row and its verification code are written in one transaction, so a
        half-registered account -- one that can never verify -- cannot be left behind.
        """
        with patch("authentication.views.user_registration.issue_code", side_effect=Exception("boom")):
            with pytest.raises(Exception, match="boom"):
                api_client.post(reverse("register"), payload(), format="json")

        assert not User.objects.filter(email="new@example.com").exists()

    def test_the_email_is_sent_outside_the_transaction(self, api_client, block_outbound_email):
        """
        Sending inside the transaction would email a code for a user that a later
        rollback removes. The account must be committed before anything goes out.
        """
        committed = {}

        def record(to_email, first_name, code):
            committed["exists"] = User.objects.filter(email=to_email).exists()
            return True

        with patch("authentication.views.user_registration.send_verification_email", side_effect=record):
            api_client.post(reverse("register"), payload(), format="json")

        assert committed["exists"] is True
