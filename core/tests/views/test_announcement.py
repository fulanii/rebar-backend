"""
The public banner.

Read by every page, signed in or not, so it must never fail on a stale token, and it
must never say which operator wrote it: the admin endpoint is where that lives.
"""

import pytest
from django.urls import reverse

from core.models import Announcement
from core.serializers import AnnouncementResponseSerializer

pytestmark = pytest.mark.django_db

URL = reverse("announcement")


@pytest.fixture
def banner(base_user):
    announcement = Announcement(message="Maintenance on Sunday.", updated_by=base_user)
    announcement.save()
    return announcement


class TestWhatIsShown:
    def test_an_active_banner_is_returned(self, api_client, banner):
        response = api_client.get(URL)

        assert response.status_code == 200
        assert response.data["message"] == "Maintenance on Sunday."

    def test_no_banner_is_null(self, api_client):
        response = api_client.get(URL)

        assert response.status_code == 200
        assert response.data is None

    def test_a_hidden_banner_reads_as_no_banner(self, api_client, banner):
        banner.is_active = False
        banner.save()

        assert api_client.get(URL).data is None


class TestShape:
    def test_the_response_carries_exactly_the_documented_fields(self, api_client, banner):
        assert set(api_client.get(URL).data) == set(AnnouncementResponseSerializer.Meta.fields)

    def test_it_never_names_the_operator_who_wrote_it(self, api_client, banner):
        """An operator's address is not for the public, and this endpoint has no auth."""
        assert "updated_by" not in api_client.get(URL).data


class TestAccess:
    def test_an_anonymous_request_is_allowed(self, api_client, banner):
        assert api_client.get(URL).status_code == 200

    def test_a_stale_token_does_not_stop_the_banner_loading(self, api_client, banner):
        """
        Authentication is switched off on purpose. With it on, an expired token turns
        the banner into a 401 on exactly the pages a signed-out person sees.
        """
        api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

        assert api_client.get(URL).status_code == 200


class TestThrottle:
    def test_the_documented_rate_is_configured(self, settings):
        """Guardrail 2: pinned here so raising it is a deliberate change to a test."""
        assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["core_announcement"] == "120/minute"

    def test_one_request_past_the_limit_is_refused(self, api_client, settings):
        limit = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["core_announcement"].split("/")[0])

        for _ in range(limit):
            api_client.get(URL)

        assert api_client.get(URL).status_code == 429
