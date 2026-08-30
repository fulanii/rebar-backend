"""Moving an account to a new email address."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from authentication.models import EmailChange
from authentication.models.one_time_code import MAX_ATTEMPTS
from authentication.utils import issue_code

User = get_user_model()

pytestmark = pytest.mark.django_db

NEW_EMAIL = "moved@example.com"


@pytest.fixture
def pending_change(base_user):
    """A live email-change code for `base_user`. Returns the raw digits."""
    with patch("authentication.utils.generate_code.secrets.randbelow", return_value=123456):
        code = issue_code(EmailChange, base_user)

    EmailChange.objects.filter(user=base_user).update(new_email=NEW_EMAIL)
    return code


def request_change(client, user_password, new_email=NEW_EMAIL):
    return client.post(
        reverse("change-email"),
        {"new_email": new_email, "password": user_password},
        format="json",
    )


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
