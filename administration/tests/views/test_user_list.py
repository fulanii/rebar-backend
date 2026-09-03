"""
The admin user list.

This endpoint answers the question every endpoint under `auth/` refuses to answer,
whether an address is registered. The access tests are therefore security tests: one
route reachable without the staff check turns the whole authentication app's
non-disclosure into a formality.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from administration.serializers import UserListResponseSerializer

pytestmark = pytest.mark.django_db


def url():
    return reverse("admin-user-list")


def client_with_real_token(user):
    """A client carrying a genuine access token, for tests of the authentication class."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


class TestAccess:
    def test_an_anonymous_request_is_refused(self, api_client):
        assert api_client.get(url()).status_code == 401

    def test_a_signed_in_user_who_is_not_staff_is_refused(self, auth_client):
        """The enumeration oracle: a 200 here would undo guardrail 4 for the whole API."""
        assert auth_client.get(url()).status_code == 403

    def test_a_staff_account_is_allowed_through(self, admin_client):
        assert admin_client.get(url()).status_code == 200

    def test_a_suspended_staff_account_is_refused(self, staff_user):
        """Suspension has to reach staff too, or revoking access leaves the list open."""
        staff_user.is_suspended = True
        staff_user.save(update_fields=["is_suspended"])

        response = client_with_real_token(staff_user).get(url())

        assert response.status_code == 401
        assert response.data["code"] == "account_suspended"


class TestRowShape:
    def test_the_row_carries_exactly_the_documented_fields(self, admin_client, base_user):
        row = admin_client.get(url()).data["results"][0]

        assert set(row) == set(UserListResponseSerializer.Meta.fields)

    @pytest.mark.parametrize("field", ["password", "groups", "user_permissions", "sessions_revoked_at"])
    def test_credential_and_session_fields_are_never_exposed(self, admin_client, base_user, field):
        """A support tool has no use for these, and an audit trail cannot unsee them."""
        assert field not in admin_client.get(url()).data["results"][0]

    def test_an_account_under_review_reports_its_state(self, admin_client, base_user):
        base_user.is_suspended = True
        base_user.save(update_fields=["is_suspended"])

        rows = {row["email"]: row for row in admin_client.get(url()).data["results"]}

        assert rows[base_user.email]["is_suspended"] is True


class TestPagination:
    def test_the_first_page_stops_at_the_default_size(self, admin_client, many_users):
        many_users(30)

        body = admin_client.get(url()).data

        assert len(body["results"]) == 25
        assert body["next"] is not None
        assert body["previous"] is None

    def test_the_newest_signup_comes_first(self, admin_client, many_users):
        many_users(3)

        results = admin_client.get(url()).data["results"]

        assert results[0]["date_joined"] > results[1]["date_joined"]

    def test_following_the_cursor_returns_every_account_exactly_once(self, admin_client, many_users):
        """
        What a page number would get wrong, and the reason this endpoint uses a cursor.

        Thirty rows over two pages, and the staff account makes thirty-one.
        """
        many_users(30)

        first = admin_client.get(url()).data
        second = admin_client.get(first["next"]).data
        seen = [row["id"] for row in first["results"] + second["results"]]

        assert len(seen) == 31
        assert len(set(seen)) == 31
        assert second["next"] is None

    def test_a_row_added_mid_read_does_not_shift_the_next_page(self, admin_client, many_users):
        """A page number would repeat a row here. The cursor holds its position."""
        many_users(30)
        first = admin_client.get(url()).data

        many_users(1, prefix="latecomer")

        second = admin_client.get(first["next"]).data
        overlap = {row["id"] for row in first["results"]} & {row["id"] for row in second["results"]}

        assert overlap == set()

    def test_the_page_size_can_be_narrowed(self, admin_client, many_users):
        many_users(30)

        assert len(admin_client.get(url(), {"page_size": 5}).data["results"]) == 5

    def test_the_page_size_is_capped(self, admin_client, many_users):
        """Without the cap, one request could ask for the entire table."""
        many_users(120)

        assert len(admin_client.get(url(), {"page_size": 500}).data["results"]) == 100

    def test_an_empty_page_is_not_an_error(self, admin_client):
        response = admin_client.get(url())

        assert response.status_code == 200
        assert len(response.data["results"]) == 1
