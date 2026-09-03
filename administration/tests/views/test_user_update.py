"""
The admin user update.

Everything this endpoint writes either moves the login itself or hands out access to
this API, which is why the route is superuser-only and why the access tests below are
the load-bearing half of the file. The other half pins what it refuses to write: no
password, ever, and never your own staff or superuser flag.
"""

import pytest
from django.urls import reverse

from administration.serializers import UserDetailResponseSerializer

pytestmark = pytest.mark.django_db


def url(user):
    return reverse("admin-user-update", args=[user.pk])


class TestAccess:
    def test_an_anonymous_request_is_refused(self, api_client, base_user):
        assert api_client.patch(url(base_user), {"first_name": "Nope"}, format="json").status_code == 401

    def test_a_signed_in_user_is_refused(self, auth_client, second_user):
        assert auth_client.patch(url(second_user), {"first_name": "Nope"}, format="json").status_code == 403

    def test_staff_alone_is_not_enough(self, admin_client, base_user):
        """The endpoint that grants staff cannot be reachable by everyone holding it."""
        response = admin_client.patch(url(base_user), {"first_name": "Nope"}, format="json")

        assert response.status_code == 403

        base_user.refresh_from_db()
        assert base_user.first_name != "Nope"

    def test_a_superuser_is_allowed_through(self, superuser_client, base_user):
        assert superuser_client.patch(url(base_user), {"first_name": "Jane"}, format="json").status_code == 200

    def test_a_suspended_superuser_is_refused(self, superuser, base_user, token_client):
        superuser.is_suspended = True
        superuser.save(update_fields=["is_suspended"])

        response = token_client(superuser).patch(url(base_user), {"first_name": "Nope"}, format="json")

        assert response.status_code == 401
        assert response.data["code"] == "account_suspended"

    def test_an_unknown_id_is_a_404(self, superuser_client, base_user):
        target = reverse("admin-user-update", args=[base_user.pk + 999])

        assert superuser_client.patch(target, {"first_name": "Jane"}, format="json").status_code == 404


class TestWhatItWrites:
    def test_it_updates_the_fields_it_is_given(self, superuser_client, base_user):
        response = superuser_client.patch(
            url(base_user),
            {"first_name": "Janet", "last_name": "Smith", "phone_number": "5559998888"},
            format="json",
        )

        base_user.refresh_from_db()
        assert response.status_code == 200
        assert (base_user.first_name, base_user.last_name, base_user.phone_number) == (
            "Janet",
            "Smith",
            "5559998888",
        )

    def test_it_leaves_everything_it_was_not_given(self, superuser_client, base_user):
        """Partial, so a field nobody mentioned cannot be cleared by omission."""
        superuser_client.patch(url(base_user), {"first_name": "Janet"}, format="json")

        base_user.refresh_from_db()
        assert base_user.last_name == "User"
        assert base_user.is_verified is True

    def test_it_moves_the_login_address(self, superuser_client, base_user):
        superuser_client.patch(url(base_user), {"email": "  NEW@Example.COM  "}, format="json")

        base_user.refresh_from_db()
        assert base_user.email == "new@example.com"

    def test_it_toggles_the_account_states(self, superuser_client, base_user):
        superuser_client.patch(url(base_user), {"is_active": False, "is_verified": False}, format="json")

        base_user.refresh_from_db()
        assert base_user.is_active is False
        assert base_user.is_verified is False

    def test_a_phone_number_can_be_cleared(self, superuser_client, base_user):
        superuser_client.patch(url(base_user), {"phone_number": ""}, format="json")

        base_user.refresh_from_db()
        assert base_user.phone_number == ""

    def test_it_answers_with_the_whole_account(self, superuser_client, base_user):
        response = superuser_client.patch(url(base_user), {"first_name": "Janet"}, format="json")

        assert set(response.data) == set(UserDetailResponseSerializer.Meta.fields)
        assert response.data["first_name"] == "Janet"


class TestWhatItRefuses:
    def test_a_password_cannot_be_set_here(self, superuser_client, base_user, user_password):
        """
        The field is not on the serializer, so this lands as an empty change, not a set.

        An operator who can set a password can sign in as the customer, and no audit
        trail can tell that apart from support work.
        """
        response = superuser_client.patch(url(base_user), {"password": "TakenOver123!"}, format="json")

        base_user.refresh_from_db()
        assert response.status_code == 400
        assert base_user.check_password(user_password)

    def test_an_empty_body_is_refused(self, superuser_client, base_user):
        response = superuser_client.patch(url(base_user), {}, format="json")

        assert response.status_code == 400
        assert "at least one field" in str(response.data).lower()

    def test_an_address_belonging_to_someone_else_is_refused(self, superuser_client, base_user, second_user):
        response = superuser_client.patch(url(base_user), {"email": second_user.email}, format="json")

        base_user.refresh_from_db()
        assert response.status_code == 400
        assert base_user.email != second_user.email

    def test_an_account_may_keep_its_own_address(self, superuser_client, base_user):
        """The uniqueness check has to exclude the row being edited, or no edit lands."""
        response = superuser_client.patch(
            url(base_user), {"email": base_user.email, "first_name": "Janet"}, format="json"
        )

        assert response.status_code == 200

    @pytest.mark.parametrize("value", ["J", "Jane9", ""])
    def test_a_name_that_fails_validation_is_refused(self, superuser_client, base_user, value):
        response = superuser_client.patch(url(base_user), {"first_name": value}, format="json")

        assert response.status_code == 400

    def test_a_phone_number_that_is_not_a_us_number_is_refused(self, superuser_client, base_user):
        response = superuser_client.patch(url(base_user), {"phone_number": "12345"}, format="json")

        assert response.status_code == 400


class TestPrivilegeFields:
    def test_a_superuser_can_grant_staff_to_somebody_else(self, superuser_client, base_user):
        response = superuser_client.patch(url(base_user), {"is_staff": True}, format="json")

        base_user.refresh_from_db()
        assert response.status_code == 200
        assert base_user.is_staff is True

    def test_nobody_grants_themselves_superuser(self, superuser_client, superuser):
        """
        The permission class cannot catch this: the caller already is a superuser.

        What it stops is a taken account editing the row it is signed in as, to lock the
        real owner out or to put the flag back on the way out.
        """
        response = superuser_client.patch(url(superuser), {"is_superuser": True}, format="json")

        assert response.status_code == 400
        assert "your own" in str(response.data).lower()

    def test_nobody_drops_their_own_staff_flag(self, superuser_client, superuser):
        response = superuser_client.patch(url(superuser), {"is_staff": False}, format="json")

        superuser.refresh_from_db()
        assert response.status_code == 400
        assert superuser.is_staff is True

    def test_editing_your_own_ordinary_fields_is_fine(self, superuser_client, superuser):
        """Only the two flags are off limits on your own row, not the whole record."""
        response = superuser_client.patch(url(superuser), {"first_name": "Rooted"}, format="json")

        superuser.refresh_from_db()
        assert response.status_code == 200
        assert superuser.first_name == "Rooted"
