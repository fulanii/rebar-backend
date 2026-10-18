"""
Editing the site-wide banner.

Reading is staff and writing is superuser, on one path, so the access tests cover each
method separately: a permission that let staff write would pass every GET test.
"""

import pytest
from django.urls import reverse

from administration.serializers import AnnouncementDetailResponseSerializer
from core.models import Announcement

pytestmark = pytest.mark.django_db

URL = reverse("admin-announcement")


@pytest.fixture
def banner(superuser):
    announcement = Announcement(message="Maintenance on Sunday.", updated_by=superuser)
    announcement.save()
    return announcement


class TestAccess:
    def test_an_anonymous_request_is_refused(self, api_client):
        assert api_client.get(URL).status_code == 401

    def test_a_signed_in_user_who_is_not_staff_cannot_read(self, auth_client):
        assert auth_client.get(URL).status_code == 403

    def test_staff_can_read(self, admin_client):
        assert admin_client.get(URL).status_code == 200

    def test_staff_cannot_write(self, admin_client):
        """The banner is shown to every visitor. Writing it is a superuser's call."""
        response = admin_client.put(URL, {"message": "Hello"}, format="json")

        assert response.status_code == 403
        assert Announcement.current() is None

    def test_staff_cannot_delete(self, admin_client, banner):
        assert admin_client.delete(URL).status_code == 403
        assert Announcement.current() is not None

    def test_a_user_who_is_not_staff_cannot_write(self, auth_client):
        assert auth_client.put(URL, {"message": "Hello"}, format="json").status_code == 403


class TestRead:
    def test_no_banner_is_null(self, admin_client):
        assert admin_client.get(URL).data is None

    def test_a_hidden_banner_is_returned_with_its_text(self, admin_client, banner):
        """The difference from the public endpoint, and the reason this one exists."""
        banner.is_active = False
        banner.save()

        response = admin_client.get(URL)

        assert response.data["message"] == "Maintenance on Sunday."
        assert response.data["is_active"] is False

    def test_the_response_carries_exactly_the_documented_fields(self, admin_client, banner):
        assert set(admin_client.get(URL).data) == set(AnnouncementDetailResponseSerializer.Meta.fields)

    def test_it_says_who_last_changed_it(self, admin_client, banner, superuser):
        assert admin_client.get(URL).data["updated_by"] == superuser.email


class TestWrite:
    def test_the_first_write_creates_the_banner(self, superuser_client):
        response = superuser_client.put(URL, {"message": "Hello"}, format="json")

        assert response.status_code == 201
        assert Announcement.current().message == "Hello"

    def test_a_later_write_replaces_it(self, superuser_client, banner):
        response = superuser_client.put(URL, {"message": "Changed"}, format="json")

        assert response.status_code == 200
        assert Announcement.objects.count() == 1
        assert Announcement.current().message == "Changed"

    def test_the_author_is_the_caller_not_the_body(self, superuser_client, superuser, base_user):
        superuser_client.put(URL, {"message": "Hello", "updated_by": base_user.pk}, format="json")

        assert Announcement.current().updated_by == superuser

    def test_an_omitted_is_active_means_shown(self, superuser_client, banner):
        """`PUT` replaces, it does not merge, so a hidden banner is shown again."""
        banner.is_active = False
        banner.save()

        superuser_client.put(URL, {"message": "Back"}, format="json")

        assert Announcement.current().is_active is True

    def test_it_can_be_hidden_without_losing_the_text(self, superuser_client, banner):
        superuser_client.put(URL, {"message": banner.message, "is_active": False}, format="json")

        assert Announcement.current().message == "Maintenance on Sunday."
        assert Announcement.current().is_active is False

    def test_the_message_is_trimmed(self, superuser_client):
        superuser_client.put(URL, {"message": "  Hello  "}, format="json")

        assert Announcement.current().message == "Hello"


class TestValidation:
    @pytest.mark.parametrize("message", ["", "   "])
    def test_an_active_banner_needs_a_message(self, superuser_client, message):
        response = superuser_client.put(URL, {"message": message}, format="json")

        assert response.status_code == 400
        assert "message" in response.data

    def test_a_hidden_banner_may_be_empty(self, superuser_client):
        response = superuser_client.put(URL, {"message": "", "is_active": False}, format="json")

        assert response.status_code == 201

    def test_the_message_is_required(self, superuser_client):
        """Otherwise a `PUT` of only `is_active` would silently wipe the text."""
        response = superuser_client.put(URL, {"is_active": False}, format="json")

        assert response.status_code == 400
        assert "message" in response.data

    def test_the_message_has_a_length_limit(self, superuser_client):
        response = superuser_client.put(URL, {"message": "x" * 256}, format="json")

        assert response.status_code == 400
        assert Announcement.current() is None


class TestDelete:
    def test_it_removes_the_banner(self, superuser_client, banner):
        assert superuser_client.delete(URL).status_code == 204
        assert Announcement.current() is None

    def test_nothing_to_delete_is_a_404(self, superuser_client):
        assert superuser_client.delete(URL).status_code == 404


class TestTheAuthorsAccountGoing:
    def test_the_banner_outlives_the_account_that_wrote_it(self, admin_client, banner, superuser):
        """`SET_NULL`, so deleting an operator never takes the site banner down."""
        superuser.delete()

        response = admin_client.get(URL)

        assert response.data["message"] == "Maintenance on Sunday."
        assert response.data["updated_by"] is None
