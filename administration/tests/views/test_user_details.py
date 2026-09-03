"""
The admin user detail.

Like the list, this endpoint confirms whether an address is registered, and here the
404 itself is the answer. The access tests are the ones that keep that confirmation
behind the staff check.
"""

import pytest
from django.urls import reverse
from django.utils import timezone

from administration.serializers import UserDetailResponseSerializer

pytestmark = pytest.mark.django_db


def url(user):
    return reverse("admin-user-detail", args=[user.pk])


class TestAccess:
    def test_an_anonymous_request_is_refused(self, api_client, base_user):
        assert api_client.get(url(base_user)).status_code == 401

    def test_a_signed_in_user_who_is_not_staff_is_refused(self, auth_client, second_user):
        """403, not 404: the permission check has to run before the lookup does."""
        assert auth_client.get(url(second_user)).status_code == 403

    def test_a_user_cannot_read_their_own_record_here_either(self, auth_client, base_user):
        """Owning the record is not the permission. `auth/me/` is the endpoint for that."""
        assert auth_client.get(url(base_user)).status_code == 403

    def test_a_staff_account_is_allowed_through(self, admin_client, base_user):
        assert admin_client.get(url(base_user)).status_code == 200

    def test_a_suspended_staff_account_is_refused(self, staff_user, base_user, token_client):
        """Suspension has to reach staff too, or revoking access leaves the record open."""
        staff_user.is_suspended = True
        staff_user.save(update_fields=["is_suspended"])

        response = token_client(staff_user).get(url(base_user))

        assert response.status_code == 401
        assert response.data["code"] == "account_suspended"


class TestLookup:
    def test_it_returns_the_account_that_was_asked_for(self, admin_client, base_user, second_user):
        """Keyed on the id in the path, never on who is asking."""
        response = admin_client.get(url(second_user))

        assert response.data["id"] == second_user.pk
        assert response.data["email"] == second_user.email

    def test_an_unknown_id_is_a_404(self, admin_client, base_user):
        response = admin_client.get(reverse("admin-user-detail", args=[base_user.pk + 999]))

        assert response.status_code == 404

    def test_a_deleted_account_is_a_404(self, admin_client, second_user):
        target = url(second_user)
        second_user.delete()

        assert admin_client.get(target).status_code == 404


class TestShape:
    def test_the_response_carries_exactly_the_documented_fields(self, admin_client, base_user):
        response = admin_client.get(url(base_user))

        assert set(response.data) == set(UserDetailResponseSerializer.Meta.fields)

    @pytest.mark.parametrize("field", ["password", "groups", "user_permissions"])
    def test_credential_fields_are_never_exposed(self, admin_client, base_user, field):
        assert field not in admin_client.get(url(base_user)).data

    def test_it_answers_whether_the_account_has_been_signed_out(self, admin_client, base_user):
        """The field the list leaves out, and the reason this endpoint has its own shape."""
        assert admin_client.get(url(base_user)).data["sessions_revoked_at"] is None

        base_user.sessions_revoked_at = timezone.now()
        base_user.save(update_fields=["sessions_revoked_at"])

        assert admin_client.get(url(base_user)).data["sessions_revoked_at"] is not None

    def test_it_reports_the_states_support_acts_on(self, admin_client, unverified_user):
        response = admin_client.get(url(unverified_user))

        assert response.data["is_active"] is False
        assert response.data["is_verified"] is False
        assert response.data["is_suspended"] is False
        assert response.data["auth_provider"] == "email"

    def test_it_reports_staff_and_superuser_flags(self, admin_client, staff_user):
        response = admin_client.get(url(staff_user))

        assert response.data["is_staff"] is True
        assert response.data["is_superuser"] is False
