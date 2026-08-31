"""Requesting a move to a new email address."""

import pytest
from django.contrib.auth import get_user_model

from authentication.models import EmailChange

from .shared import NEW_EMAIL, request_change

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestRequestChange:
    def test_issues_a_code_for_the_new_address(self, auth_client, base_user, user_password):
        response = request_change(auth_client, user_password)

        assert response.status_code == 200
        assert EmailChange.objects.get(user=base_user).new_email == NEW_EMAIL

    def test_the_code_goes_to_the_new_address_only(self, auth_client, base_user, user_password, block_outbound_email):
        request_change(auth_client, user_password)

        assert block_outbound_email.called is True

    def test_the_account_address_does_not_change_yet(self, auth_client, base_user, user_password):
        request_change(auth_client, user_password)

        base_user.refresh_from_db()
        assert base_user.email != NEW_EMAIL

    def test_asking_again_replaces_the_pending_address(self, auth_client, base_user, user_password):
        request_change(auth_client, user_password)
        request_change(auth_client, user_password, new_email="second@example.com")

        assert EmailChange.objects.filter(user=base_user).count() == 1
        assert EmailChange.objects.get(user=base_user).new_email == "second@example.com"

    def test_the_wrong_password_is_rejected(self, auth_client, base_user):
        response = request_change(auth_client, "WrongPass123!")

        assert response.status_code == 400
        assert EmailChange.objects.filter(user=base_user).exists() is False

    def test_your_own_address_is_rejected(self, auth_client, base_user, user_password):
        response = request_change(auth_client, user_password, new_email=base_user.email)

        assert response.status_code == 400
        assert "new_email" in response.data

    def test_a_verified_address_is_rejected(self, auth_client, second_user, user_password):
        response = request_change(auth_client, user_password, new_email=second_user.email)

        assert response.status_code == 400
        assert "new_email" in response.data

    def test_an_unverified_address_is_available(self, auth_client, unverified_user, user_password):
        response = request_change(auth_client, user_password, new_email=unverified_user.email)

        assert response.status_code == 200

    def test_google_accounts_cannot_use_it(self, api_client, db, user_password):
        google_user = User.objects.create_user(
            email="google@example.com",
            first_name="Goo",
            last_name="Gle",
            is_active=True,
            is_verified=True,
            auth_provider=User.AuthProvider.GOOGLE,
        )
        google_user.set_unusable_password()
        google_user.save()
        api_client.force_authenticate(user=google_user)

        response = request_change(api_client, user_password)

        assert response.status_code == 400
        assert "password" in response.data

    def test_requires_authentication(self, api_client, user_password):
        assert request_change(api_client, user_password).status_code == 401
