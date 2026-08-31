"""Editing the name on your own account."""

import pytest
from django.urls import reverse
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db

URL = "profile-update"


def update(client, **fields):
    return client.patch(reverse(URL), fields, format="json")


class TestUpdateName:
    def test_changes_the_first_name(self, auth_client, base_user):
        response = update(auth_client, first_name="Janet")

        assert response.status_code == 200
        base_user.refresh_from_db()
        assert base_user.first_name == "Janet"

    def test_changes_the_last_name(self, auth_client, base_user):
        update(auth_client, last_name="Okonkwo")

        base_user.refresh_from_db()
        assert base_user.last_name == "Okonkwo"

    def test_changes_both_at_once(self, auth_client, base_user):
        update(auth_client, first_name="Ada", last_name="Lovelace")

        base_user.refresh_from_db()
        assert (base_user.first_name, base_user.last_name) == ("Ada", "Lovelace")

    def test_an_omitted_field_is_left_alone(self, auth_client, base_user):
        original = base_user.last_name

        update(auth_client, first_name="Janet")

        base_user.refresh_from_db()
        assert base_user.last_name == original

    def test_names_are_trimmed(self, auth_client, base_user):
        update(auth_client, first_name="  Janet  ")

        base_user.refresh_from_db()
        assert base_user.first_name == "Janet"

    @pytest.mark.parametrize("name", ["O'Brien", "Smith-Jones", "van der Berg", "Zoë", "Müller"])
    def test_real_names_are_accepted(self, auth_client, base_user, name):
        assert update(auth_client, last_name=name).status_code == 200

    def test_returns_the_whole_profile(self, auth_client, base_user):
        """Same shape as `GET auth/me/`, so a client can replace its cached user."""
        response = update(auth_client, first_name="Janet")

        assert response.data == auth_client.get(reverse("me")).data


class TestUpdateValidation:
    @pytest.mark.parametrize("field", ["first_name", "last_name"])
    def test_a_one_character_name_is_rejected(self, auth_client, base_user, field):
        response = update(auth_client, **{field: "J"})

        assert response.status_code == 400
        assert field in response.data

    @pytest.mark.parametrize("name", ["Jane123", "Jane!", "<script>"])
    def test_names_with_symbols_are_rejected(self, auth_client, base_user, name):
        assert update(auth_client, first_name=name).status_code == 400

    @pytest.mark.parametrize("field", ["first_name", "last_name"])
    def test_a_blank_name_is_rejected(self, auth_client, base_user, field):
        response = update(auth_client, **{field: ""})

        assert response.status_code == 400
        assert field in response.data

    def test_an_empty_body_is_rejected(self, auth_client, base_user):
        """A request that changes nothing must not look like one that worked."""
        response = update(auth_client)

        assert response.status_code == 400
        assert "Send at least one field to change." in str(response.data)

    def test_nothing_is_written_when_validation_fails(self, auth_client, base_user):
        original = base_user.first_name

        update(auth_client, first_name="J")

        base_user.refresh_from_db()
        assert base_user.first_name == original


class TestUpdateCannotReachOtherFields:
    """
    The serializer names two fields; everything else is ignored rather than applied.

    Each of these is a privilege escalation or an identity takeover if it ever writes.
    """

    def test_the_email_address_cannot_be_changed_here(self, auth_client, base_user):
        original = base_user.email

        response = update(auth_client, first_name="Janet", email="attacker@example.com")

        assert response.status_code == 200
        base_user.refresh_from_db()
        assert base_user.email == original

    def test_the_phone_number_cannot_be_changed_here(self, auth_client, base_user):
        original = base_user.phone_number

        update(auth_client, first_name="Janet", phone_number="5559999999")

        base_user.refresh_from_db()
        assert base_user.phone_number == original

    @pytest.mark.parametrize("field", ["is_staff", "is_superuser", "is_suspended", "is_verified"])
    def test_permission_and_status_flags_cannot_be_set(self, auth_client, base_user, field):
        original = getattr(base_user, field)

        update(auth_client, first_name="Janet", **{field: not original})

        base_user.refresh_from_db()
        assert getattr(base_user, field) == original

    def test_the_password_cannot_be_set(self, auth_client, base_user, user_password):
        update(auth_client, first_name="Janet", password="AttackerPass123!")

        base_user.refresh_from_db()
        assert base_user.check_password(user_password) is True

    def test_the_auth_provider_cannot_be_switched(self, auth_client, base_user):
        update(auth_client, first_name="Janet", auth_provider="google")

        base_user.refresh_from_db()
        assert base_user.auth_provider == "email"

    def test_another_account_is_untouched(self, auth_client, base_user, second_user):
        original = second_user.first_name

        update(auth_client, first_name="Janet", id=second_user.pk)

        second_user.refresh_from_db()
        assert second_user.first_name == original


class TestUpdateAccess:
    def test_requires_authentication(self, api_client):
        assert update(api_client, first_name="Janet").status_code == 401

    def test_a_suspended_account_is_refused(self, api_client, base_user):
        base_user.is_suspended = True
        base_user.save(update_fields=["is_suspended"])

        token = RefreshToken.for_user(base_user).access_token
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        assert update(api_client, first_name="Janet").status_code == 401

    @pytest.mark.parametrize("method", ["post", "put", "delete"])
    def test_only_patch_is_allowed(self, auth_client, base_user, method):
        response = getattr(auth_client, method)(reverse(URL), {"first_name": "Janet"}, format="json")

        assert response.status_code == 405

    def test_sessions_are_left_alone(self, auth_client, base_user):
        """Nothing here changes how the account is signed in to, so nothing is revoked."""
        RefreshToken.for_user(base_user)

        update(auth_client, first_name="Janet")

        base_user.refresh_from_db()
        assert base_user.sessions_revoked_at is None
        assert BlacklistedToken.objects.filter(token__user=base_user).count() == 0

    def test_no_email_is_sent(self, auth_client, base_user, block_outbound_email):
        block_outbound_email.reset_mock()

        update(auth_client, first_name="Janet")

        assert block_outbound_email.called is False
