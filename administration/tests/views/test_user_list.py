"""
The admin user list.

This endpoint answers the question every endpoint under `auth/` refuses to answer,
whether an address is registered. The access tests are therefore security tests: one
route reachable without the staff check turns the whole authentication app's
non-disclosure into a formality.
"""

import pytest
from django.urls import reverse

from administration.serializers import UserListQueryResponseSerializer

pytestmark = pytest.mark.django_db


def url():
    return reverse("admin-user-list")


class TestAccess:
    def test_an_anonymous_request_is_refused(self, api_client):
        assert api_client.get(url()).status_code == 401

    def test_a_signed_in_user_who_is_not_staff_is_refused(self, auth_client):
        """The enumeration oracle: a 200 here would undo guardrail 4 for the whole API."""
        assert auth_client.get(url()).status_code == 403

    def test_a_staff_account_is_allowed_through(self, admin_client):
        assert admin_client.get(url()).status_code == 200

    def test_a_suspended_staff_account_is_refused(self, staff_user, token_client):
        """Suspension has to reach staff too, or revoking access leaves the list open."""
        staff_user.is_suspended = True
        staff_user.save(update_fields=["is_suspended"])

        response = token_client(staff_user).get(url())

        assert response.status_code == 401
        assert response.data["code"] == "account_suspended"


class TestRowShape:
    def test_the_row_carries_exactly_the_documented_fields(self, admin_client, base_user):
        row = admin_client.get(url()).data["results"][0]

        assert set(row) == set(UserListQueryResponseSerializer.Meta.fields)

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

    def test_the_total_is_counted(self, admin_client, many_users):
        """Thirty rows, and the staff account makes thirty-one."""
        many_users(30)

        assert admin_client.get(url()).data["count"] == 31

    def test_the_newest_signup_comes_first(self, admin_client, many_users):
        many_users(3)

        results = admin_client.get(url()).data["results"]

        assert results[0]["date_joined"] > results[1]["date_joined"]

    @pytest.mark.parametrize("ordering", ["-date_joined", "first_name", "-last_login"])
    def test_following_next_returns_every_account_exactly_once(self, admin_client, many_users, ordering):
        """
        Under ties too: every `many_users` row is called "Test" and none has signed in.

        Without `id` as a tiebreak, rows sharing a sort value have no defined order, and
        the database may return them differently per page, repeating or skipping them.
        """
        many_users(30)

        first = admin_client.get(url(), {"ordering": ordering, "page_size": 10}).data
        pages = [first]

        while pages[-1]["next"]:
            pages.append(admin_client.get(pages[-1]["next"]).data)

        seen = [row["id"] for page in pages for row in page["results"]]

        assert len(seen) == 31
        assert len(set(seen)) == 31

    def test_next_carries_the_filters_along(self, admin_client, many_users):
        many_users(30)

        first = admin_client.get(url(), {"search": "user1", "page_size": 5}).data
        second = admin_client.get(first["next"]).data

        assert all("user1" in row["email"] for row in second["results"])

    def test_a_signup_mid_read_repeats_one_row_on_the_next_page(self, admin_client, many_users):
        """
        The trade-off page numbers make, pinned so it reads as a decision and not a bug.

        A new signup pushes every row down by one, so the last row of page one reappears
        at the top of page two. If an `as_of` snapshot is added, this test flips.
        """
        many_users(30)
        first = admin_client.get(url()).data

        many_users(1, prefix="latecomer")

        second = admin_client.get(first["next"]).data
        overlap = {row["id"] for row in first["results"]} & {row["id"] for row in second["results"]}

        assert len(overlap) == 1

    def test_the_page_size_can_be_narrowed(self, admin_client, many_users):
        many_users(30)

        assert len(admin_client.get(url(), {"page_size": 5}).data["results"]) == 5

    def test_the_page_size_is_capped(self, admin_client, many_users):
        """Without the cap, one request could ask for the entire table."""
        many_users(120)

        assert len(admin_client.get(url(), {"page_size": 500}).data["results"]) == 100

    @pytest.mark.parametrize("page", ["99", "zero"])
    def test_a_page_that_does_not_exist_is_a_404(self, admin_client, page):
        assert admin_client.get(url(), {"page": page}).status_code == 404

    def test_an_empty_page_is_not_an_error(self, admin_client):
        response = admin_client.get(url())

        assert response.status_code == 200
        assert len(response.data["results"]) == 1


class TestFiltersOverHttp:
    """The filters themselves are tested in tests/utils; this is the route wiring."""

    def test_a_filter_narrows_the_list(self, admin_client, base_user):
        response = admin_client.get(url(), {"is_staff": "true"})

        assert [row["email"] for row in response.data["results"]] == ["operator@example.com"]

    def test_an_invalid_parameter_is_a_400_naming_it(self, admin_client):
        """Never the whole table returned as if it were the filtered result."""
        response = admin_client.get(url(), {"ordering": "password", "is_staff": "maybe"})

        assert response.status_code == 400
        assert set(response.data) == {"ordering", "is_staff"}

    def test_a_filter_does_not_get_past_the_staff_check(self, auth_client):
        """The permission runs before the query, so a filter cannot be used to probe."""
        assert auth_client.get(url(), {"search": "operator"}).status_code == 403
