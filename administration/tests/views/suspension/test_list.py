"""
The suspension history.

This is the record half of the feature: the flag on the account says whether somebody
is locked out right now, and these rows say how many times it has happened, why, and
who signed off on it. A list that quietly dropped lifted rows would answer the first
question twice and the second one never.
"""

import pytest
from django.urls import reverse

from administration.models import Suspension

pytestmark = pytest.mark.django_db


def url():
    return reverse("admin-suspension-list")


@pytest.fixture
def suspensions(superuser, base_user, second_user):
    """One open suspension, and one that was lifted."""
    open_record = Suspension.objects.create(user=base_user, reason="fraud", suspended_by=superuser)
    lifted = Suspension.objects.create(user=second_user, reason="spam", suspended_by=superuser)
    lifted.lifted_at = lifted.suspended_at
    lifted.lifted_by = superuser
    lifted.save(update_fields=["lifted_at", "lifted_by"])
    return open_record, lifted


class TestAccess:
    def test_an_anonymous_request_is_refused(self, api_client):
        assert api_client.get(url()).status_code == 401

    def test_a_signed_in_user_is_refused(self, auth_client):
        assert auth_client.get(url()).status_code == 403

    def test_staff_alone_is_not_enough(self, admin_client):
        """Consistent with the rest of the flow: suspensions are a superuser matter."""
        assert admin_client.get(url()).status_code == 403

    def test_a_superuser_is_allowed_through(self, superuser_client):
        assert superuser_client.get(url()).status_code == 200


class TestContents:
    def test_it_lists_open_and_lifted_alike(self, superuser_client, suspensions):
        """History, not current state. Dropping the lifted rows would erase the history."""
        results = superuser_client.get(url()).data["results"]

        assert len(results) == 2
        assert {row["reason"] for row in results} == {"fraud", "spam"}
        assert sum(1 for row in results if row["lifted_at"] is None) == 1

    def test_a_row_carries_the_whole_record(self, superuser_client, superuser, base_user, suspensions):
        row = next(r for r in superuser_client.get(url()).data["results"] if r["user"] == base_user.pk)

        assert set(row) == {
            "id",
            "user",
            "reason",
            "notes",
            "suspended_at",
            "suspended_by",
            "lifted_at",
            "lifted_by",
        }
        assert row["suspended_by"] == superuser.email

    def test_the_operator_is_named_by_email(self, superuser_client, superuser, suspensions):
        """An id here would mean a second call to find out who it was."""
        row = superuser_client.get(url()).data["results"][0]

        assert row["suspended_by"] == superuser.email

    def test_an_empty_history_is_not_an_error(self, superuser_client):
        response = superuser_client.get(url())

        assert response.status_code == 200
        assert response.data["results"] == []


class TestPagination:
    def test_the_first_page_stops_at_the_default_size(self, superuser_client, superuser, base_user):
        Suspension.objects.bulk_create(
            Suspension(user=base_user, reason="manual", suspended_by=superuser) for _ in range(30)
        )

        body = superuser_client.get(url()).data

        assert len(body["results"]) == 25
        assert body["next"] is not None

    def test_following_the_cursor_returns_every_row_exactly_once(self, superuser_client, superuser, base_user):
        Suspension.objects.bulk_create(
            Suspension(user=base_user, reason="manual", suspended_by=superuser) for _ in range(30)
        )

        first = superuser_client.get(url()).data
        second = superuser_client.get(first["next"]).data
        seen = [row["id"] for row in first["results"] + second["results"]]

        assert len(seen) == len(set(seen)) == 30
        assert second["next"] is None

    def test_the_newest_suspension_comes_first(self, superuser_client, superuser, base_user):
        for reason in ("spam", "abuse", "fraud"):
            Suspension.objects.create(user=base_user, reason=reason, suspended_by=superuser)

        results = superuser_client.get(url()).data["results"]

        assert results[0]["reason"] == "fraud"
        assert results[-1]["reason"] == "spam"

    def test_the_page_size_is_capped(self, superuser_client, superuser, base_user):
        Suspension.objects.bulk_create(
            Suspension(user=base_user, reason="manual", suspended_by=superuser) for _ in range(120)
        )

        assert len(superuser_client.get(url(), {"page_size": 500}).data["results"]) == 100
