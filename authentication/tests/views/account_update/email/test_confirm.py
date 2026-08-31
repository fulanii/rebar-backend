"""Confirming a move to a new email address."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from authentication.models.one_time_code import MAX_ATTEMPTS

from .shared import NEW_EMAIL

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestConfirmChange:
    def test_the_correct_code_moves_the_account(self, auth_client, base_user, pending_change):
        response = auth_client.post(reverse("change-email-confirm"), {"code": pending_change}, format="json")

        assert response.status_code == 200
        assert response.data["email"] == NEW_EMAIL
        base_user.refresh_from_db()
        assert base_user.email == NEW_EMAIL

    def test_the_code_cannot_be_replayed(self, auth_client, base_user, pending_change):
        auth_client.post(reverse("change-email-confirm"), {"code": pending_change}, format="json")
        response = auth_client.post(reverse("change-email-confirm"), {"code": pending_change}, format="json")

        assert response.status_code == 400

    def test_a_wrong_code_leaves_the_address_alone(self, auth_client, base_user, pending_change):
        response = auth_client.post(reverse("change-email-confirm"), {"code": "000000"}, format="json")

        assert response.status_code == 400
        base_user.refresh_from_db()
        assert base_user.email != NEW_EMAIL

    def test_the_code_dies_after_five_wrong_guesses(self, auth_client, base_user, pending_change, unlimited_requests):
        for _ in range(MAX_ATTEMPTS):
            auth_client.post(reverse("change-email-confirm"), {"code": "000000"}, format="json")

        response = auth_client.post(reverse("change-email-confirm"), {"code": pending_change}, format="json")

        assert response.status_code == 400
        base_user.refresh_from_db()
        assert base_user.email != NEW_EMAIL

    def test_no_pending_change_gives_the_same_error(self, auth_client, base_user):
        response = auth_client.post(reverse("change-email-confirm"), {"code": "123456"}, format="json")

        assert response.status_code == 400
        assert response.data["detail"] == "Invalid or expired code."

    def test_an_address_claimed_in_the_meantime_is_refused(self, auth_client, base_user, pending_change):
        User.objects.create_user(
            email=NEW_EMAIL,
            password="SomeoneElse123!",
            first_name="Some",
            last_name="Body",
            is_active=True,
            is_verified=True,
        )

        response = auth_client.post(reverse("change-email-confirm"), {"code": pending_change}, format="json")

        assert response.status_code == 400
        base_user.refresh_from_db()
        assert base_user.email != NEW_EMAIL

    def test_sessions_survive_the_change(self, auth_client, base_user, pending_change):
        auth_client.post(reverse("change-email-confirm"), {"code": pending_change}, format="json")

        assert auth_client.get(reverse("me")).status_code == 200

    def test_the_new_address_is_the_login(self, api_client, base_user, pending_change, auth_client, user_password):
        auth_client.post(reverse("change-email-confirm"), {"code": pending_change}, format="json")

        response = api_client.post(
            reverse("login"),
            {"email": NEW_EMAIL, "password": user_password},
            format="json",
        )

        assert response.status_code == 200

    def test_requires_authentication(self, api_client):
        assert api_client.post(reverse("change-email-confirm"), {"code": "123456"}, format="json").status_code == 401
