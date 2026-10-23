"""
The admin overview figures.

Counts only, but counts of registered accounts are still something the routes under
`auth/` refuse to reveal, so the access tests matter as much as the arithmetic.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from administration.serializers import StatsResponseSerializer
from authentication.models import CustomUser

pytestmark = pytest.mark.django_db

URL = reverse("admin-stats")


def joined(days_ago, email):
    user = CustomUser.objects.create(email=email, first_name="Test", last_name="Person")
    CustomUser.objects.filter(pk=user.pk).update(date_joined=timezone.now() - timedelta(days=days_ago))


class TestAccess:
    def test_an_anonymous_request_is_refused(self, api_client):
        assert api_client.get(URL).status_code == 401

    def test_a_signed_in_user_who_is_not_staff_is_refused(self, auth_client):
        assert auth_client.get(URL).status_code == 403

    def test_staff_can_read(self, admin_client):
        assert admin_client.get(URL).status_code == 200


class TestFigures:
    def test_the_response_carries_exactly_the_documented_fields(self, admin_client):
        assert set(admin_client.get(URL).data) == set(StatsResponseSerializer().fields)

    def test_every_account_counts(self, admin_client, base_user, unverified_user):
        """Unverified and staff included: the same accounts the unfiltered list shows."""
        assert admin_client.get(URL).data["total_users"] == 3

    def test_only_the_last_seven_days_count_as_recent(self, admin_client):
        joined(1, "yesterday@example.com")
        joined(6, "six-days@example.com")
        joined(8, "last-week@example.com")
        joined(200, "long-ago@example.com")

        data = admin_client.get(URL).data

        assert data["total_users"] == 5
        assert data["signups_last_7_days"] == 3
